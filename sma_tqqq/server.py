"""Local HTTP server: fetches fresh data per visit and serves the dashboard."""

import html
import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import backtest, chart, config, fred, nasdaq, stats, web

_lock = threading.Lock()

DECADE_TTL = 86400
FRED_TTL = 10 * 365 * 86400


def _iso(ts):
    if not ts:
        return "never"
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def gather(force=False):
    bt_err = dc_err = None
    tq10 = fred_ndx = fred_ff = None
    with _lock:
        tq_rows, m_th = nasdaq.cached(
            "tqqq_history", config.history_ttl_seconds(),
            lambda: nasdaq.fetch_history("TQQQ", "etf"), force)
        try:
            tq_q, m_tq = nasdaq.cached(
                "tqqq_quote", config.quote_ttl_seconds(),
                lambda: nasdaq.fetch_quote("TQQQ", "etf"), force)
        except Exception as e:
            tq_q, m_tq = None, {"fetched_at": 0, "stale": True, "error": str(e)}
        try:
            tq10, _ = nasdaq.cached(
                "tqqq_history_10y", DECADE_TTL,
                lambda: nasdaq.fetch_history("TQQQ", "etf", days_back=3645), force)
        except Exception as e:
            bt_err = str(e)
        try:
            fred_ndx, _ = nasdaq.cached(
                "fred_ndx_1998_2003", FRED_TTL,
                lambda: fred.fetch_series("NASDAQ100", "1998-01-01", "2003-12-31"))
            fred_ff, _ = nasdaq.cached(
                "fred_fedfunds_1998_2004", FRED_TTL,
                lambda: fred.fetch_series("FEDFUNDS", "1998-01-01", "2004-01-31"))
        except Exception as e:
            dc_err = str(e)

    s = stats.compute(tq_rows, tq_q)

    if tq10:
        try:
            s["backtest"] = backtest.decade(tq10)
        except Exception as e:
            s["backtest"] = {"available": False, "error": str(e)}
    else:
        s["backtest"] = {"available": False, "error": bt_err or "ten year history unavailable"}

    bt = s["backtest"]
    if bt.get("available") and fred_ndx and fred_ff:
        try:
            wealth = {k: bt[k]["final"] for k in ("hold", "sig2")}
            s["dotcom"] = backtest.dotcom(tq10, fred_ndx, fred_ff, wealth)
        except Exception as e:
            s["dotcom"] = {"available": False, "error": str(e)}
    else:
        s["dotcom"] = {"available": False, "error": dc_err or "needs the ten year backtest and the FRED series"}

    metas = [m_th, m_tq]
    stale = any(m.get("stale") for m in metas)
    errors = [m.get("error") for m in metas if m.get("error")]
    meta = {
        "stale": stale,
        "error": "; ".join(errors) if errors else None,
        "oldest_fetch": _iso(min(m.get("fetched_at", 0) for m in metas)),
        "history_fetched": _iso(m_th.get("fetched_at", 0)),
    }
    return s, meta


class Handler(BaseHTTPRequestHandler):
    server_version = "sma-tqqq"

    def _send(self, code, body, ctype):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        force = parse_qs(url.query).get("refresh", ["0"])[0] == "1"
        try:
            if url.path == "/healthz":
                self._send(200, "ok", "text/plain; charset=utf-8")
            elif url.path == "/api/status":
                s, meta = gather(force)
                out = {k: v for k, v in s.items() if k not in ("chart_series", "charts")}
                for k in ("backtest", "dotcom"):
                    if isinstance(out.get(k), dict):
                        out[k] = {kk: vv for kk, vv in out[k].items()
                                  if kk not in ("series", "chart", "price_series", "chart_tq")}
                out["meta"] = meta
                self._send(200, json.dumps(out, indent=2), "application/json")
            elif url.path == "/":
                s, meta = gather(force)
                dates = [d for d, _, _, _ in s["chart_series"]]
                lines = [
                    ("TQQQ", "--s1", [c for _, c, _, _ in s["chart_series"]]),
                    ("SMA5", "--s2", [a for _, _, a, _ in s["chart_series"]]),
                    ("SMA218", "--s3", [b for _, _, _, b in s["chart_series"]]),
                ]
                s["charts"] = [
                    ("tq", "The signal: TQQQ close vs its 5 and 218 day averages, last %d sessions" % len(dates),
                     lines, chart.build("tq", dates, lines)),
                ]
                for key, prefix in (("backtest", "bt"), ("dotcom", "dc")):
                    sec = s.get(key) or {}
                    if sec.get("available"):
                        ser = sec["series"]
                        eq_lines = [
                            ("Hold TQQQ", "--s1", ser["hold"]),
                            ("5/218 signal", "--s3", ser["sig2"]),
                        ]
                        sec["chart"] = {
                            "lines": eq_lines,
                            "built": chart.build(prefix, ser["dates"], eq_lines, log=True),
                        }
                dc = s.get("dotcom") or {}
                if dc.get("available") and dc.get("price_series"):
                    ps = dc["price_series"]
                    mark = (ps["boundary"], "today = the 2000 peak")
                    tlines = [
                        ("TQQQ", "--s1", ps["tqqq"]["close"]),
                        ("SMA5", "--s2", ps["tqqq"]["sma5"]),
                        ("SMA218", "--s3", ps["tqqq"]["sma218"]),
                    ]
                    dc["chart_tq"] = {
                        "lines": tlines,
                        "built": chart.build("dct", ps["tqqq"]["dates"], tlines, mark=mark),
                    }
                self._send(200, web.render(s, meta), "text/html; charset=utf-8")
            else:
                self._send(404, "not found", "text/plain; charset=utf-8")
        except Exception as e:
            msg = (
                "<!doctype html><title>SMA-TQQQ error</title>"
                "<body style=\"font-family:system-ui;padding:40px\">"
                "<h2>SMA-TQQQ could not build the page</h2><p>%s</p>"
                "<p>No cached data is available yet. Check the internet connection and "
                "<a href=\"/\">try again</a>.</p></body>" % html.escape(str(e))
            )
            self._send(500, msg, "text/html; charset=utf-8")


def main():
    host, port = config.host(), config.port()
    print("sma-tqqq %s listening on http://%s:%d" % (
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), host, port))
    server = ThreadingHTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
