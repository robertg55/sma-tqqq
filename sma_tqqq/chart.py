"""Renders multi line SVG charts with hover data."""

import json
import math

W, H = 920, 300
PAD_L, PAD_R, PAD_T, PAD_B = 64, 100, 18, 30


def _path(xs, ys):
    parts = []
    for i in range(len(xs)):
        parts.append("%s%.2f %.2f" % ("M" if i == 0 else "L", xs[i], ys[i]))
    return " ".join(parts)


def _axis_label(v, hi):
    if hi >= 2000:
        return format(int(round(v)), ",")
    return format(v, ",.1f")


def build(prefix, dates, lines, log=False, mark=None):
    """lines is a list of (label, css var, values), each aligned with dates."""
    n = len(dates)
    tr = math.log10 if log else (lambda v: v)
    lo = min(min(vals) for _, _, vals in lines)
    hi = max(max(vals) for _, _, vals in lines)
    tlo = tr(lo)
    thi = tr(hi)
    span = (thi - tlo) or 1.0
    tlo -= span * 0.05
    thi += span * 0.05
    if not log and lo >= 0:
        tlo = max(tlo, 0.0)

    def x_at(i):
        return PAD_L + (W - PAD_L - PAD_R) * (i / (n - 1))

    def y_at(v):
        return PAD_T + (H - PAD_T - PAD_B) * (1 - (tr(v) - tlo) / (thi - tlo))

    xs = [round(x_at(i), 2) for i in range(n)]
    parts = []
    for k in range(5):
        tv = tlo + (thi - tlo) * k / 4
        v = 10 ** tv if log else tv
        y = PAD_T + (H - PAD_T - PAD_B) * (1 - (tv - tlo) / (thi - tlo))
        parts.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--grid)" stroke-width="1"/>' % (PAD_L, W - PAD_R, y, y))
        parts.append('<text x="%d" y="%.1f" text-anchor="end" class="axis">%s</text>' % (PAD_L - 8, y + 4, _axis_label(v, hi)))
    for frac, i in ((0.0, 0), (0.5, n // 2), (1.0, n - 1)):
        anchor = "start" if frac == 0.0 else ("middle" if frac == 0.5 else "end")
        parts.append('<text x="%.1f" y="%d" text-anchor="%s" class="axis">%s</text>' % (xs[i], H - 8, anchor, dates[i]))
    parts.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--axis)" stroke-width="1"/>' % (PAD_L, W - PAD_R, H - PAD_B, H - PAD_B))

    if mark:
        mi, mlabel = mark
        parts.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="var(--ink2)" stroke-width="1" stroke-dasharray="5 4"/>' % (xs[mi], xs[mi], PAD_T, H - PAD_B))
        parts.append('<text x="%.1f" y="%d" text-anchor="middle" class="axis">%s</text>' % (xs[mi], PAD_T - 5, mlabel))

    meta = []
    for label, var, vals in lines:
        ys = [round(y_at(v), 2) for v in vals]
        parts.append('<path d="%s" fill="none" stroke="var(%s)" stroke-width="2" stroke-linejoin="round"/>' % (_path(xs, ys), var))
        meta.append({"label": label, "var": var, "vals": [round(v, 2) for v in vals], "ys": ys})

    order = sorted(range(len(lines)), key=lambda k: meta[k]["ys"][-1])
    label_y = {}
    prev = None
    for k in order:
        y = meta[k]["ys"][-1]
        if prev is not None and y < prev + 14:
            y = prev + 14
        label_y[k] = y
        prev = y
    for k, m in enumerate(meta):
        parts.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(%s)" stroke="var(--surface)" stroke-width="2"/>' % (xs[-1], m["ys"][-1], m["var"]))
        parts.append('<text x="%.1f" y="%.1f" class="endlab">%s</text>' % (xs[-1] + 10, label_y[k] + 4, m["label"]))

    parts.append('<line id="xline-%s" x1="0" x2="0" y1="%d" y2="%d" stroke="var(--muted)" stroke-width="1" stroke-dasharray="3 3" style="display:none"/>' % (prefix, PAD_T, H - PAD_B))
    for k, m in enumerate(meta):
        parts.append('<circle id="dot-%s-%d" r="4" fill="var(%s)" stroke="var(--surface)" stroke-width="2" style="display:none"/>' % (prefix, k, m["var"]))
    parts.append('<rect x="%d" y="%d" width="%d" height="%d" fill="transparent"/>' % (PAD_L, PAD_T, W - PAD_L - PAD_R, H - PAD_T - PAD_B))

    names = " vs ".join(l for l, _, _ in lines)
    svg = '<svg id="chart-svg-%s" viewBox="0 0 %d %d" role="img" aria-label="%s">%s</svg>' % (prefix, W, H, names, "".join(parts))
    data = {
        "w": W,
        "dates": dates,
        "xs": xs,
        "series": [{"label": m["label"], "vals": m["vals"], "ys": m["ys"]} for m in meta],
    }
    return {"svg": svg, "data_json": json.dumps(data)}
