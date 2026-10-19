"""Renders the index vs SMA200 chart as inline SVG with hover data."""

import json

W, H = 920, 300
PAD_L, PAD_R, PAD_T, PAD_B = 64, 100, 18, 30


def _path(xs, ys):
    parts = []
    for i in range(len(xs)):
        parts.append("%s%.2f %.2f" % ("M" if i == 0 else "L", xs[i], ys[i]))
    return " ".join(parts)


def _thousands(v):
    return format(int(round(v)), ",")


def build(series):
    dates = [s[0] for s in series]
    close = [s[1] for s in series]
    sma = [s[2] for s in series]
    lo = min(min(close), min(sma))
    hi = max(max(close), max(sma))
    span = (hi - lo) or 1.0
    lo -= span * 0.05
    hi += span * 0.05
    n = len(series)

    def x_at(i):
        return PAD_L + (W - PAD_L - PAD_R) * (i / (n - 1))

    def y_at(v):
        return PAD_T + (H - PAD_T - PAD_B) * (1 - (v - lo) / (hi - lo))

    xs = [round(x_at(i), 2) for i in range(n)]
    y_close = [round(y_at(v), 2) for v in close]
    y_sma = [round(y_at(v), 2) for v in sma]

    grid = []
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        y = y_at(v)
        grid.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--grid)" stroke-width="1"/>' % (PAD_L, W - PAD_R, y, y))
        grid.append('<text x="%d" y="%.1f" text-anchor="end" class="axis">%s</text>' % (PAD_L - 8, y + 4, _thousands(v)))
    for frac, idx in ((0.0, 0), (0.5, n // 2), (1.0, n - 1)):
        anchor = "start" if frac == 0.0 else ("middle" if frac == 0.5 else "end")
        grid.append('<text x="%.1f" y="%d" text-anchor="%s" class="axis">%s</text>' % (xs[idx], H - 8, anchor, dates[idx]))

    end_items = (
        '<circle cx="%.1f" cy="%.1f" r="4" fill="var(--s1)" stroke="var(--surface)" stroke-width="2"/>'
        '<circle cx="%.1f" cy="%.1f" r="4" fill="var(--s2)" stroke="var(--surface)" stroke-width="2"/>'
        '<text x="%.1f" y="%.1f" class="endlab">NDX</text>'
        '<text x="%.1f" y="%.1f" class="endlab">SMA200</text>'
    ) % (
        xs[-1], y_close[-1],
        xs[-1], y_sma[-1],
        xs[-1] + 10, y_close[-1] + 4,
        xs[-1] + 10, y_sma[-1] + 4,
    )

    svg = (
        '<svg id="chart-svg" viewBox="0 0 %d %d" role="img" aria-label="Nasdaq-100 close versus its 200 day moving average">' % (W, H)
        + "".join(grid)
        + '<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--axis)" stroke-width="1"/>' % (PAD_L, W - PAD_R, H - PAD_B, H - PAD_B)
        + '<path d="%s" fill="none" stroke="var(--s2)" stroke-width="2" stroke-linejoin="round"/>' % _path(xs, y_sma)
        + '<path d="%s" fill="none" stroke="var(--s1)" stroke-width="2" stroke-linejoin="round"/>' % _path(xs, y_close)
        + end_items
        + '<line id="xline" x1="0" x2="0" y1="%d" y2="%d" stroke="var(--muted)" stroke-width="1" stroke-dasharray="3 3" style="display:none"/>' % (PAD_T, H - PAD_B)
        + '<circle id="dot1" r="4" fill="var(--s1)" stroke="var(--surface)" stroke-width="2" style="display:none"/>'
        + '<circle id="dot2" r="4" fill="var(--s2)" stroke="var(--surface)" stroke-width="2" style="display:none"/>'
        + '<rect x="%d" y="%d" width="%d" height="%d" fill="transparent"/>' % (PAD_L, PAD_T, W - PAD_L - PAD_R, H - PAD_T - PAD_B)
        + "</svg>"
    )

    data = {
        "w": W,
        "dates": dates,
        "close": close,
        "sma": [round(v, 2) for v in sma],
        "xs": xs,
        "ys1": y_close,
        "ys2": y_sma,
    }
    return {"svg": svg, "data_json": json.dumps(data)}
