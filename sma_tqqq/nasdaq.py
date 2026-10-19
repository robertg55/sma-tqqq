"""Fetches history and quotes from Nasdaq's public API, with a small file cache."""

import json
import time
import urllib.request
from datetime import date, timedelta

from . import config

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com/",
}

API = "https://api.nasdaq.com/api/quote/{symbol}/{kind}"


class FetchError(RuntimeError):
    pass


def _get_json(url):
    last = None
    for _ in range(2):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as r:
                data = json.loads(r.read())
            code = (data.get("status") or {}).get("rCode")
            if code not in (200, None):
                raise FetchError("nasdaq api returned rCode %s" % code)
            return data
        except Exception as e:
            last = e
            time.sleep(1.5)
    raise FetchError(str(last))


def _num(s):
    if s is None:
        return None
    s = str(s).replace("$", "").replace(",", "").replace("%", "").strip()
    if s in ("", "--", "N/A", "NA"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def fetch_history(symbol, assetclass, days_back=1100):
    start = (date.today() - timedelta(days=days_back)).isoformat()
    end = date.today().isoformat()
    url = (
        API.format(symbol=symbol, kind="historical")
        + "?assetclass=%s&fromdate=%s&todate=%s&limit=99999" % (assetclass, start, end)
    )
    data = _get_json(url)
    rows = ((data.get("data") or {}).get("tradesTable") or {}).get("rows") or []
    out = []
    for r in rows:
        c = _num(r.get("close"))
        if c is None:
            continue
        m, d, y = r["date"].split("/")
        out.append({"date": "%s-%s-%s" % (y, m, d), "close": c})
    out.sort(key=lambda r: r["date"])
    if len(out) < 220:
        raise FetchError("history too short for %s: %d rows" % (symbol, len(out)))
    return out


def fetch_quote(symbol, assetclass):
    url = API.format(symbol=symbol, kind="info") + "?assetclass=" + assetclass
    data = _get_json(url)
    d = data.get("data") or {}
    p = d.get("primaryData") or {}
    return {
        "price": _num(p.get("lastSalePrice")),
        "change_pct": _num(p.get("percentageChange")),
        "when": p.get("lastTradeTimestamp") or "",
        "market": d.get("marketStatus") or "",
    }


def cached(name, ttl_seconds, fetcher, force=False):
    path = config.data_dir() / (name + ".json")
    now = time.time()
    old = None
    if path.exists():
        try:
            old = json.loads(path.read_text())
        except Exception:
            old = None
    if old and not force and now - old.get("fetched_at", 0) < ttl_seconds:
        return old["payload"], {"fetched_at": old["fetched_at"], "stale": False, "error": None}
    try:
        payload = fetcher()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"fetched_at": now, "payload": payload}))
        return payload, {"fetched_at": now, "stale": False, "error": None}
    except Exception as e:
        if old:
            return old["payload"], {"fetched_at": old.get("fetched_at", 0), "stale": True, "error": str(e)}
        raise
