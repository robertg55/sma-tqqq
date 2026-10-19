"""Fetches historical series from FRED's public CSV endpoint."""

import time
import urllib.request

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s&cosd=%s&coed=%s"
HEADERS = {"User-Agent": "sma-tqqq/1.0 (+https://github.com/robertg55/sma-tqqq)"}


def fetch_series(series_id, start, end):
    """Returns [[date, value], ...] oldest first, skipping blank observations."""
    last = None
    for _ in range(2):
        try:
            req = urllib.request.Request(URL % (series_id, start, end), headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                text = r.read().decode("utf-8", "replace")
            out = []
            for line in text.splitlines()[1:]:
                parts = line.split(",")
                if len(parts) != 2:
                    continue
                try:
                    out.append([parts[0].strip(), float(parts[1])])
                except ValueError:
                    continue
            if len(out) < 10:
                raise RuntimeError("FRED returned no usable rows for %s" % series_id)
            return out
        except Exception as e:
            last = e
            time.sleep(1.5)
    raise RuntimeError(str(last))
