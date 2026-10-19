"""Builds the dashboard HTML page."""

import html
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
  color-scheme: light;
  --page:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7; --border:rgba(11,11,11,0.10);
  --s1:#2a78d6; --s2:#eb6834;
  --good:#0ca30c; --crit:#d03b3b; --warn:#fab219;
}
@media (prefers-color-scheme: dark){
  :root{
    color-scheme: dark;
    --page:#0d0d0d; --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,0.10);
    --s1:#3987e5; --s2:#d95926;
  }
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
  border:1px solid var(--border);border-left:6px solid $verdict_color;border-radius:10px;
  padding:16px 20px;margin-bottom:12px}
.verdict .icon{font-size:22px;color:$verdict_color}
.verdict .title{font-size:19px;font-weight:700}
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
#chart-wrap{position:relative}
#chart-svg{width:100%;height:auto;display:block}
#chart-tip{display:none;position:absolute;background:var(--surface);border:1px solid var(--border);
  border-radius:8px;padding:8px 10px;font-size:12px;color:var(--ink2);pointer-events:none;
  box-shadow:0 2px 10px rgba(0,0,0,0.12);font-variant-numeric:tabular-nums}
.axis{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}
.endlab{fill:var(--ink2);font-size:12px}
details{background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:10px 16px;margin-bottom:12px;color:var(--ink2)}
summary{cursor:pointer;font-size:13px}
table{border-collapse:collapse;margin-top:10px;font-variant-numeric:tabular-nums;font-size:13px}
td,th{padding:4px 14px 4px 0;text-align:right;border-bottom:1px solid var(--grid)}
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
<div class="verdict">
  <div class="icon">$verdict_icon</div>
  <div>
    <div class="title">$verdict_title</div>
    <div class="sub">$verdict_sub</div>
  </div>
</div>
<div class="grid">
$cards_html
</div>
<div class="chart-card">
  <p class="chart-title">Nasdaq-100 close vs 200 day average, last $n_sessions sessions</p>
  <div class="legend">
    <span><span class="sw" style="background:var(--s1)"></span>NDX close</span>
    <span><span class="sw" style="background:var(--s2)"></span>SMA200</span>
  </div>
  <div id="chart-wrap">
    $chart_svg
    <div id="chart-tip"></div>
  </div>
</div>
<details>
  <summary>Data table, last 15 sessions</summary>
  <table>
    <tr><th>Date</th><th>NDX close</th><th>SMA200</th><th>Gap</th></tr>
    $table_rows
  </table>
</details>
<footer>
  Rule: hold TQQQ while the Nasdaq-100 official close is above the average of its last 200 closes, otherwise sit in cash.
  Decisions use official closes only; the live quote is informational.
  Data comes from Nasdaq's public API and is cached locally in data/ (never committed).
  Page auto refreshes every 5 minutes. Mechanical indicator, not financial advice.
</footer>
</div>
<script type="application/json" id="chart-data">$chart_data</script>
<script>
(function(){
  var data = JSON.parse(document.getElementById("chart-data").textContent);
  var svg = document.getElementById("chart-svg");
  var tip = document.getElementById("chart-tip");
  var line = document.getElementById("xline");
  var d1 = document.getElementById("dot1");
  var d2 = document.getElementById("dot2");
  function fmt(v){return v.toLocaleString(undefined,{maximumFractionDigits:2});}
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
    d1.setAttribute("cx", x); d1.setAttribute("cy", data.ys1[best]); d1.style.display = "block";
    d2.setAttribute("cx", x); d2.setAttribute("cy", data.ys2[best]); d2.style.display = "block";
    var gap = (data.close[best] / data.sma[best] - 1) * 100;
    tip.innerHTML = "<b>" + data.dates[best] + "</b><br>NDX " + fmt(data.close[best]) +
      "<br>SMA200 " + fmt(data.sma[best]) + "<br>gap " + (gap >= 0 ? "+" : "") + gap.toFixed(2) + "%";
    tip.style.display = "block";
    var px = x * r.width / data.w;
    tip.style.left = Math.min(Math.max(px + 14, 8), r.width - 160) + "px";
    tip.style.top = "6px";
  }
  function hide(){
    tip.style.display = "none"; line.style.display = "none";
    d1.style.display = "none"; d2.style.display = "none";
  }
  svg.addEventListener("pointermove", show);
  svg.addEventListener("pointerleave", hide);
})();
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


def render(s, meta):
    ndx = s["ndx"]
    tq = s["tqqq"]
    live = s["live"]
    in_market = s["signal"] == "TQQQ"

    if in_market:
        verdict_color = "var(--good)"
        verdict_icon = "&#9650;"
        verdict_title = "IN MARKET: hold or buy TQQQ"
    else:
        verdict_color = "var(--crit)"
        verdict_icon = "&#9632;"
        verdict_title = "OUT: sell TQQQ, stay in cash"
    verdict_sub = "NDX closed %s on %s, %s the 200 day line at %s (%s). In this state for %d sessions, since %s." % (
        _n(ndx["close"]), ndx["date"],
        "above" if in_market else "below",
        _n(ndx["sma200"]), _pct(ndx["gap_pct"]),
        ndx["days_in_state"], ndx["state_since"],
    )

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
        "Signal flips tomorrow on a close %s" % ("below" if in_market else "above"),
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
        "Line crossings, past year",
        str(ndx["crossings_1y"]),
        "each crossing is one trade for the plain rule",
    ))
    cards.append(_card(
        "NDX volatility, 20 day",
        "%.0f%% annualized" % ndx["vol20_pct"],
        "decade averages: 22% above the line, 41% below it",
    ))

    table_rows = []
    for d, c, m in s["chart_series"][-15:][::-1]:
        table_rows.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (d, _n(c), _n(m), _pct((c / m - 1) * 100))
        )

    stale_html = ""
    if meta.get("stale"):
        age = meta.get("oldest_fetch", "")
        err = html.escape(meta.get("error") or "fetch failed")
        stale_html = (
            '<div class="stale"><span style="color:var(--warn);font-size:18px">&#9888;</span>'
            "<span><b>Showing cached data</b> (last good fetch %s). Latest attempt: %s</span></div>" % (age, err)
        )

    chart = s["chart_html"]
    return PAGE.substitute(
        now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        market=html.escape((live or {}).get("market") or "unknown"),
        stale_html=stale_html,
        verdict_color=verdict_color,
        verdict_icon=verdict_icon,
        verdict_title=verdict_title,
        verdict_sub=verdict_sub,
        cards_html="\n".join(cards),
        n_sessions=str(len(s["chart_series"])),
        chart_svg=chart["svg"],
        chart_data=chart["data_json"],
        table_rows="\n".join(table_rows),
    )
