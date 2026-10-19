"""Builds the dashboard HTML page."""

import html
import json
from datetime import datetime, timezone
from string import Template

PAGE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>SMA-TQQQ</title>
<style>
:root{
  color-scheme: dark;
  --page:#0d0d0d; --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,0.10);
  --s1:#3987e5; --s2:#d95926; --s3:#199e70;
  --good:#0ca30c; --crit:#d03b3b; --warn:#fab219;
}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);
  font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;padding:24px 16px}
.wrap{max-width:980px;margin:0 auto}
header{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px;margin-bottom:14px}
h1{font-size:20px;margin:0}
.meta{color:var(--ink2);font-size:12px}
.meta a{color:var(--ink2)}
.verdict{display:flex;align-items:center;gap:14px;background:var(--surface);
  border:1px solid var(--border);border-radius:10px;
  padding:14px 20px;margin-bottom:12px}
.verdict .icon{font-size:22px}
.verdict .title{font-size:18px;font-weight:700}
.verdict .sub{color:var(--ink2);font-size:13px;margin-top:2px}
.stale{display:flex;gap:10px;align-items:center;background:var(--surface);border:1px solid var(--border);
  border-left:6px solid var(--warn);border-radius:10px;padding:10px 16px;margin-bottom:12px;
  color:var(--ink2);font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(225px,1fr));gap:12px;margin-bottom:12px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:13px 16px}
.k{font-size:12px;color:var(--muted);margin-bottom:5px}
.v{font-size:19px;font-weight:600;font-variant-numeric:tabular-nums}
.sub{font-size:12px;color:var(--ink2);margin-top:4px}
.chart-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:16px;margin-bottom:12px}
.chart-title{font-size:14px;font-weight:600;margin:0 0 4px}
.legend{display:flex;gap:18px;font-size:12px;color:var(--ink2);margin-bottom:8px}
.sw{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.chart-wrap{position:relative}
.chart-wrap svg{width:100%;height:auto;display:block}
.tip{display:none;position:absolute;background:var(--surface);border:1px solid var(--border);
  border-radius:8px;padding:8px 10px;font-size:12px;color:var(--ink2);pointer-events:none;
  box-shadow:0 2px 10px rgba(0,0,0,0.35);font-variant-numeric:tabular-nums}
.axis{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}
.endlab{fill:var(--ink2);font-size:12px}
details{background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:10px 16px;margin-bottom:12px;color:var(--ink2)}
summary{cursor:pointer;font-size:13px}
table{border-collapse:collapse;margin-top:10px;font-variant-numeric:tabular-nums;font-size:13px}
td,th{padding:4px 12px 4px 0;text-align:right;border-bottom:1px solid var(--grid)}
td:first-child,th:first-child{text-align:left}
footer{color:var(--muted);font-size:12px;line-height:1.6}
footer a{color:var(--ink2)}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>SMA-TQQQ</h1>
  <span class="meta">rendered $now UTC &middot; market $market &middot;
    <a href="/?refresh=1">refresh data now</a> &middot; <a href="/api/status">json</a></span>
</header>
$stale_html
$banners_html
<div class="grid">
$cards_html
</div>
$charts_html
<details>
  <summary>Data table, last 15 sessions</summary>
  <table>
    <tr><th>Date</th><th>NDX close</th><th>SMA200</th><th>Gap</th><th>TQQQ</th><th>SMA5</th><th>SMA218</th></tr>
    $table_rows
  </table>
</details>
<footer>
  Signal 1 (SMA200): hold TQQQ while the Nasdaq-100 official close is above the average of its last 200 closes, otherwise cash.
  Signal 2 (5/218): hold TQQQ while its own 5 day average is above its 218 day average, otherwise cash.
  Decisions use official closes only; the live quote is informational.
  Data comes from Nasdaq's public API and is cached locally in data/ (never committed).
  Page auto refreshes every 5 minutes. Mechanical indicators, not financial advice.
</footer>
</div>
<script type="application/json" id="chart-prefixes">$prefixes_json</script>
<script>
function initChart(p){
  var data = JSON.parse(document.getElementById("chart-data-" + p).textContent);
  var svg = document.getElementById("chart-svg-" + p);
  var tip = document.getElementById("chart-tip-" + p);
  var line = document.getElementById("xline-" + p);
  var dots = data.series.map(function(_, k){ return document.getElementById("dot-" + p + "-" + k); });
  function fmt(v){ return v.toLocaleString(undefined, {maximumFractionDigits: 2}); }
  function show(e){
    var r = svg.getBoundingClientRect();
    var vx = (e.clientX - r.left) * data.w / r.width;
    var best = 0, bd = 1e9;
    for (var i = 0; i < data.xs.length; i++){
      var d = Math.abs(data.xs[i] - vx);
      if (d < bd){ bd = d; best = i; }
    }
    var x = data.xs[best];
    line.setAttribute("x1", x); line.setAttribute("x2", x); line.style.display = "block";
    var rows = "<b>" + data.dates[best] + "</b>";
    data.series.forEach(function(s, k){
      dots[k].setAttribute("cx", x);
      dots[k].setAttribute("cy", s.ys[best]);
      dots[k].style.display = "block";
      rows += "<br>" + s.label + " " + fmt(s.vals[best]);
    });
    tip.innerHTML = rows;
    tip.style.display = "block";
    var px = x * r.width / data.w;
    tip.style.left = Math.min(Math.max(px + 14, 8), r.width - 170) + "px";
    tip.style.top = "6px";
  }
  function hide(){
    tip.style.display = "none";
    line.style.display = "none";
    dots.forEach(function(d){ d.style.display = "none"; });
  }
  svg.addEventListener("pointermove", show);
  svg.addEventListener("pointerleave", hide);
}
JSON.parse(document.getElementById("chart-prefixes").textContent).forEach(initChart);
</script>
</body>
</html>
""")


def _n(v, dec=2):
    return format(v, ",.%df" % dec)


def _pct(v, dec=2):
    return ("%+." + str(dec) + "f") % v + "%"


def _card(k, v, sub=""):
    out = '<div class="card"><div class="k">%s</div><div class="v">%s</div>' % (k, v)
    if sub:
        out += '<div class="sub">%s</div>' % sub
    return out + "</div>"


def _banner(in_market, label, title, sub):
    color = "var(--good)" if in_market else "var(--crit)"
    icon = "&#9650;" if in_market else "&#9632;"
    return (
        '<div class="verdict" style="border-left:6px solid %s">'
        '<div class="icon" style="color:%s">%s</div>'
        '<div><div class="title">%s <span style="color:var(--muted);font-weight:400;font-size:13px">(%s)</span></div>'
        '<div class="sub">%s</div></div></div>' % (color, color, icon, title, label, sub)
    )


def render(s, meta):
    ndx = s["ndx"]
    tq = s["tqqq"]
    t2 = s["tqqq_5218"]
    live = s["live"]
    in1 = s["signal"] == "TQQQ"
    in2 = t2["signal"] == "TQQQ"

    banners = []
    banners.append(_banner(
        in1,
        "signal 1: index SMA200",
        "IN MARKET: hold or buy TQQQ" if in1 else "OUT: sell TQQQ, stay in cash",
        "NDX closed %s on %s, %s the 200 day line at %s (%s). In this state %d sessions, since %s." % (
            _n(ndx["close"]), ndx["date"],
            "above" if in1 else "below",
            _n(ndx["sma200"]), _pct(ndx["gap_pct"]),
            ndx["days_in_state"], ndx["state_since"]),
    ))
    banners.append(_banner(
        in2,
        "signal 2: TQQQ 5/218",
        "IN MARKET: hold or buy TQQQ" if in2 else "OUT: sell TQQQ, stay in cash",
        "TQQQ 5 day average %s is %s the 218 day average %s (%s). In this state %d sessions, since %s." % (
            _n(t2["sma5"]), "above" if in2 else "below",
            _n(t2["sma218"]), _pct(t2["gap_pct"]),
            t2["days_in_state"], t2["state_since"]),
    ))

    cards = []
    cards.append(_card(
        "Official NDX close (%s)" % ndx["date"],
        _n(ndx["close"]),
        "day change %s" % _pct(ndx["day_change_pct"]),
    ))
    cards.append(_card(
        "200 day average",
        _n(ndx["sma200"]),
        "gap to line %s" % _pct(ndx["gap_pct"]),
    ))
    cards.append(_card(
        "Signal 1 flips tomorrow on a close %s" % ("below" if in1 else "above"),
        _n(ndx["flip_level"]),
        "2%% band exit level: %s" % _n(ndx["band_level"]),
    ))
    if live:
        cards.append(_card(
            "Live NDX (%s)" % html.escape(live["market"] or "quote"),
            _n(live["price"]),
            "provisional signal if the session closed now: %s (%s vs line)" % (
                live["provisional_signal"], _pct(live["gap_pct"])),
        ))
    tq_quote = tq.get("quote") or {}
    tq_sub = "day change %s" % _pct(tq["day_change_pct"])
    if tq_quote.get("when"):
        tq_sub += " &middot; last trade %s" % html.escape(str(tq_quote["when"]))
    cards.append(_card("TQQQ last close (%s)" % tq["date"], _n(tq["last"]), tq_sub))
    cards.append(_card(
        "TQQQ 5 and 218 day averages",
        "%s / %s" % (_n(t2["sma5"]), _n(t2["sma218"])),
        "signal 2 gap %s, %d crossings in the past year" % (_pct(t2["gap_pct"]), t2["crossings_1y"]),
    ))
    cards.append(_card(
        "TQQQ 1 year peak",
        _n(tq["peak_1y"]),
        "current drawdown %s, 1y low %s" % (_pct(tq["drawdown_pct"]), _n(tq["low_1y"])),
    ))
    cards.append(_card(
        "40% crash brake (secondary)",
        _n(tq["brake_level"]),
        "TQQQ is %s this level; from the deep drawdown backtests" % ("above" if tq["above_brake"] else "BELOW"),
    ))
    cards.append(_card(
        "SMA200 crossings, past year",
        str(ndx["crossings_1y"]),
        "each crossing is one trade for signal 1",
    ))
    cards.append(_card(
        "NDX volatility, 20 day",
        "%.0f%% annualized" % ndx["vol20_pct"],
        "decade averages: 22% above the line, 41% below it",
    ))

    charts_html = []
    prefixes = []
    for prefix, title, lines, built in s["charts"]:
        prefixes.append(prefix)
        legend = "".join(
            '<span><span class="sw" style="background:var(%s)"></span>%s</span>' % (var, label)
            for label, var, _ in lines
        )
        charts_html.append(
            '<div class="chart-card"><p class="chart-title">%s</p>'
            '<div class="legend">%s</div>'
            '<div class="chart-wrap">%s<div id="chart-tip-%s" class="tip"></div></div>'
            '<script type="application/json" id="chart-data-%s">%s</script></div>'
            % (title, legend, built["svg"], prefix, prefix, built["data_json"])
        )

    t2map = {d: (c, a, b) for d, c, a, b in s["chart2_series"]}
    table_rows = []
    for d, c, m in s["chart_series"][-15:][::-1]:
        tq_cells = "<td></td><td></td><td></td>"
        if d in t2map:
            tc, ta, tb = t2map[d]
            tq_cells = "<td>%s</td><td>%s</td><td>%s</td>" % (_n(tc), _n(ta), _n(tb))
        table_rows.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td>%s</tr>"
            % (d, _n(c), _n(m), _pct((c / m - 1) * 100), tq_cells)
        )

    stale_html = ""
    if meta.get("stale"):
        age = meta.get("oldest_fetch", "")
        err = html.escape(meta.get("error") or "fetch failed")
        stale_html = (
            '<div class="stale"><span style="color:var(--warn);font-size:18px">&#9888;</span>'
            "<span><b>Showing cached data</b> (last good fetch %s). Latest attempt: %s</span></div>" % (age, err)
        )

    return PAGE.substitute(
        now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        market=html.escape((live or {}).get("market") or "unknown"),
        stale_html=stale_html,
        banners_html="\n".join(banners),
        cards_html="\n".join(cards),
        charts_html="\n".join(charts_html),
        table_rows="\n".join(table_rows),
        prefixes_json=json.dumps(prefixes),
    )
