"""Local HTTP server: fetches fresh data per visit and serves the dashboard."""

import html
import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import chart, config, nasdaq, stats, web

_lock = threading.Lock()


def _iso(ts):
    if not ts:
        return "never"
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def gather(force=False):
    with _lock:
        ndx_rows, m_nh = nasdaq.cached(
            "ndx_history", config.history_ttl_seconds(),
            lambda: nasdaq.fetch_history("NDX", "index"), force)
        tq_rows, m_th = nasdaq.cached(
            "tqqq_history", config.history_ttl_seconds(),
            lambda: nasdaq.fetch_history("TQQQ", "etf"), force)
        try:
            ndx_q, m_nq = nasdaq.cached(
                "ndx_quote", config.quote_ttl_seconds(),
                lambda: nasdaq.fetch_quote("NDX", "index"), force)
        except Exception as e:
            ndx_q, m_nq = None, {"fetched_at": 0, "stale": True, "error": str(e)}
        try:
            tq_q, m_tq = nasdaq.cached(
                "tqqq_quote", config.quote_ttl_seconds(),
                lambda: nasdaq.fetch_quote("TQQQ", "etf"), force)
        except Exception as e:
            tq_q, m_tq = None, {"fetched_at": 0, "stale": True, "error": str(e)}

    s = stats.compute(ndx_rows, tq_rows, ndx_q, tq_q)
    metas = [m_nh, m_th, m_nq, m_tq]
    stale = any(m.get("stale") for m in metas)
    errors = [m.get("error") for m in metas if m.get("error")]
    meta = {
        "stale": stale,
        "error": "; ".join(errors) if errors else None,
        "oldest_fetch": _iso(min(m.get("fetched_at", 0) for m in metas)),
        "history_fetched": _iso(m_nh.get("fetched_at", 0)),
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
                out = {k: v for k, v in s.items() if k != "chart_series"}
                out["meta"] = meta
                self._send(200, json.dumps(out, indent=2), "application/json")
            elif url.path == "/":
                s, meta = gather(force)
                s["chart_html"] = chart.build(s["chart_series"])
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
