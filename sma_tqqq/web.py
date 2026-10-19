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
h2{font-size:16px;margin:22px 0 8px}
.secnote{color:var(--ink2);font-size:13px;line-height:1.55;margin:0 0 10px}
.note{color:var(--muted);font-size:12px;line-height:1.5;margin:10px 0 0}
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
.explain summary{font-weight:600;color:var(--ink)}
.explain p{font-size:13px;color:var(--ink2);line-height:1.6;margin:10px 0 2px}
.explain b{color:var(--ink)}
.tscroll{overflow-x:auto}
table{border-collapse:collapse;margin-top:10px;font-variant-numeric:tabular-nums;font-size:13px}
td,th{padding:4px 12px 4px 0;text-align:right;border-bottom:1px solid var(--grid);white-space:nowrap}
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
$explain_html
<div class="grid">
$cards_html
</div>
$charts_html
$backtest_html
$dotcom_html
<details>
  <summary>Data table, last 15 sessions</summary>
  <table>
    <tr><th>Date</th><th>TQQQ close</th><th>SMA5</th><th>SMA218</th><th>Gap</th></tr>
    $table_rows
  </table>
</details>
<footer>
  The signal (TQQQ 5/218): hold TQQQ while its own 5 day average close is above its 218 day average, otherwise cash.
  Decisions use official closes only; the live quote is informational.
  The backtest and the crash replay are simulations under the assumptions stated next to them.
  Data comes from Nasdaq's public API (and FRED for the 2000 era) and is cached locally in data/ (never committed).
  Page auto refreshes every 5 minutes. A mechanical indicator, not financial advice.
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
var ex = document.getElementById("explain");
if (ex){
  try {
    if (localStorage.getItem("smaExplain") === "1") ex.open = true;
    ex.addEventListener("toggle", function(){
      localStorage.setItem("smaExplain", ex.open ? "1" : "0");
    });
  } catch (err) {}
}
</script>
</body>
</html>
""")

EXPLAIN = (
    '<details class="explain" id="explain">'
    "<summary>How it works: TQQQ and the signal, in plain words</summary>"
    "<p><b>What TQQQ is.</b> TQQQ is a fund that moves 3 times as much as the Nasdaq-100 index, every day, "
    "in both directions. When the index gains 1% in a day, TQQQ gains about 3%; when the index drops 2%, TQQQ drops "
    "about 6%. Over a long rising market that compounding is spectacular, but in a crash it is lethal: TQQQ lost "
    "about 80% in 2022, and in a repeat of the 2000 crash it loses over 99%. The whole game is to own it while the "
    "market is healthy and to not own it during disasters.</p>"
    "<p><b>The signal: the TQQQ 5/218 crossover.</b> Average TQQQ's last 5 closing prices (a fast line) and its "
    "last 218 closes (a slow line that tracks the long term trend). The rule: be in TQQQ while the fast line is "
    "above the slow one, and sit in cash while it is below; the day they cross, you trade. Why it works: average "
    "returns are about the same on both sides of a long moving average, but the violence is not. Volatility below "
    "the line runs roughly twice as high, and nearly all of the catastrophic days happen down there. A daily 3x "
    "fund is destroyed by exactly that chaos, so skipping it matters more than catching every rebound day. Using "
    "a 5 day average instead of a single close filters out one day head fakes, so the signal trades rarely, at "
    "the price of reacting a few days later at real turning points.</p>"
    "<p><b>How to use the page.</b> Check the banner once a day after the market close. Green means be invested; "
    "red means be in cash. There is no prediction involved, the rule only reacts to its own moving averages. The "
    "receipts are below: a backtest over the last ten years of real prices, and a replay of the 2000 dot-com "
    "crash starting tomorrow. A mechanical rule, not financial advice.</p>"
    "</details>"
)

STRATS = (
    ("Buy and hold TQQQ", "--s1", "hold"),
    ("The 5/218 signal", "--s3", "sig2"),
)


def _n(v, dec=2):
    return format(v, ",.%df" % dec)


def _pct(v, dec=2):
    return format(v, "+,.%df" % dec) + "%"


def _money(v):
    return "$" + format(int(round(v)), ",")


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


def _chart_block(prefix, title, lines, built, extra=""):
    legend = "".join(
        '<span><span class="sw" style="background:var(%s)"></span>%s</span>' % (var, label)
        for label, var, _ in lines
    )
    return (
        '<div class="chart-card"><p class="chart-title">%s</p>'
        '<div class="legend">%s</div>'
        '<div class="chart-wrap">%s<div id="chart-tip-%s" class="tip"></div></div>'
        '%s<script type="application/json" id="chart-data-%s">%s</script></div>'
        % (title, legend, built["svg"], prefix, extra, prefix, built["data_json"])
    )


def _bt_table(bt):
    rows = [
        "<tr><th>Strategy</th><th>Final wealth</th><th>Total return</th><th>Per year</th>"
        "<th>Worst drop</th><th>Time invested</th><th>Trades</th></tr>"
    ]
    for name, var, key in STRATS:
        r = bt[key]
        rows.append(
            '<tr><td><span class="sw" style="background:var(%s)"></span>%s</td>'
            "<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%.0f%%</td><td>%d</td></tr>"
            % (var, name, _money(r["final"]), _pct(r["total_return_pct"], 0),
               _pct(r["cagr_pct"], 1), _pct(r["max_drawdown_pct"], 1),
               r["time_in_market_pct"], r["trades"])
        )
    return '<div class="tscroll"><table>%s</table></div>' % "".join(rows)


def _dc_table(dc):
    exits = {"hold": None, "sig2": dc.get("sig2_exit")}
    rows = [
        "<tr><th>Strategy</th><th>Start (today)</th><th>First sell</th><th>3 months in</th>"
        "<th>At the index bottom</th><th>End of replay</th><th>Worst drop</th><th>Trades</th></tr>"
    ]
    for name, var, key in STRATS:
        r = dc[key]
        e = exits[key]
        first = "day %d" % e["session"] if e else "never"
        rows.append(
            '<tr><td><span class="sw" style="background:var(%s)"></span>%s</td>'
            "<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%d</td></tr>"
            % (var, name, _money(r["start"]), first, _money(r["after_3_months"]),
               _money(r["at_bottom"]), _money(r["final"]),
               _pct(r["max_drawdown_pct"], 2), r["trades"])
        )
    return '<div class="tscroll"><table>%s</table></div>' % "".join(rows)


def _backtest_section(bt, prefixes):
    head = "<h2>Backtest: the last ten years</h2>"
    if not bt:
        return ""
    if not (bt.get("available") and bt.get("chart")):
        return head + '<div class="stale">The backtest could not run: %s</div>' % html.escape(str(bt.get("error", "unknown")))
    note = (
        "One decision per session at the official close, trades fill at that same close. "
        "Cash earns nothing. Taxes, fees and dividends are ignored. The signal needs a long "
        "average, so the race starts on the first session where a full 218 day history exists "
        "inside the fetched decade of data."
    )
    secnote = (
        '<p class="secnote">Both lines invest %s on %s and follow their rule through %s. '
        "This is how the banner above would actually have traded, next to simply buying "
        "and holding TQQQ the whole time.</p>"
        % (_money(bt["start_cash"]), bt["start"], bt["end"])
    )
    ch = bt["chart"]
    extra = _bt_table(bt) + '<p class="note">%s</p>' % note
    prefixes.append("bt")
    title = "Growth of %s, %s to %s (log scale)" % (_money(bt["start_cash"]), bt["start"], bt["end"])
    return head + secnote + _chart_block("bt", title, ch["lines"], ch["built"], extra)


def _dotcom_section(dc, prefixes):
    head = "<h2>Stress test: a dot-com crash starting tomorrow</h2>"
    if not dc:
        return ""
    if not (dc.get("available") and dc.get("chart")):
        return head + '<div class="stale">The crash replay could not run: %s</div>' % html.escape(str(dc.get("error", "unknown")))
    e2 = dc.get("sig2_exit")
    alt = dc.get("today_gap_exits") or {}
    timing = ""
    if e2:
        timing = (
            " The crossing lands exactly where it did in 2000: the signal sells %d sessions after the peak "
            "(%s, TQQQ %s from the top)."
            % (e2["session"], e2["date"], _pct(e2["tqqq_drop_pct"], 1))
        )
        if alt.get("sig2_day"):
            timing += (
                " For reference, if the crash days were instead applied against today's real averages, with "
                "their much smaller gap, the sell would come on day %d."
                % alt["sig2_day"]
            )
    secnote = (
        '<p class="secnote">Today stands at the exact 2000-03-27 peak. The year left of the divider is the '
        "real 1999 to 2000 melt-up with every price scaled so the peak equals today's close, which puts both "
        "averages exactly where they sat at the top: the peak closed with the 5 day average %s above the "
        "218 day line, far more than today's real %s, so the crash runs for a while before they cross. From "
        "there the index fell %.0f%% to the October 2002 bottom and was still %.0f%% down at the end of "
        "2003.%s</p>"
        % (_pct(dc["peak_gap_pct"], 1), _pct(dc["today_gap_pct"], 1),
           abs(dc["ndx_at_bottom_pct"]), abs(dc["ndx_at_end_pct"]), timing)
    )
    out = head + secnote
    ch_t = dc.get("chart_tq")
    if ch_t:
        prefixes.append("dct")
        t2 = "Sell trigger: TQQQ vs 5 and 218 day averages, melt-up and crash at today's prices"
        if e2:
            t2 += " (sells day %d)" % e2["session"]
        out += _chart_block("dct", t2, ch_t["lines"], ch_t["built"])
    note = (
        "TQQQ is simulated at 3 times each daily index move minus the financing drag of that era's interest "
        "rates, the same reconstruction that matches the real fund since 2016. Scaling every price by one "
        "factor moves no crossing, so the sell day and the whipsaws match the real 2000 to 2003 tape. Index "
        "path %s to %s from FRED; axis dates are hypothetical sessions standing in for that era. Both "
        "strategies begin the replay with their final wealth from the backtest above."
        % (dc["replayed_from"], dc["replayed_to"])
    )
    ch = dc["chart"]
    extra = _dc_table(dc) + '<p class="note">%s</p>' % note
    prefixes.append("dc")
    return out + _chart_block("dc", "Wealth through the full replay (log scale)", ch["lines"], ch["built"], extra)


def render(s, meta):
    tq = s["tqqq"]
    t2 = s["tqqq_5218"]
    live = s["live"]
    inm = t2["signal"] == "TQQQ"

    banners = [_banner(
        inm,
        "TQQQ 5/218",
        "IN MARKET: hold or buy TQQQ" if inm else "OUT: sell TQQQ, stay in cash",
        "TQQQ 5 day average %s is %s the 218 day average %s (%s). In this state %d sessions, since %s." % (
            _n(t2["sma5"]), "above" if inm else "below",
            _n(t2["sma218"]), _pct(t2["gap_pct"]),
            t2["days_in_state"], t2["state_since"]),
    )]

    cards = []
    tq_quote = tq.get("quote") or {}
    tq_sub = "day change %s" % _pct(tq["day_change_pct"])
    if tq_quote.get("when"):
        tq_sub += " &middot; last trade %s" % html.escape(str(tq_quote["when"]))
    cards.append(_card("TQQQ last close (%s)" % tq["date"], _n(tq["last"]), tq_sub))
    if live:
        cards.append(_card(
            "Live TQQQ (%s)" % html.escape(live["market"] or "quote"),
            _n(live["price"]),
            "provisional signal if the session closed now: %s (gap %s)" % (
                live["provisional_signal"], _pct(live["gap_pct"])),
        ))
    cards.append(_card(
        "5 and 218 day averages",
        "%s / %s" % (_n(t2["sma5"]), _n(t2["sma218"])),
        "gap %s, %d crossings in the past year" % (_pct(t2["gap_pct"]), t2["crossings_1y"]),
    ))
    if t2["flip_level"] > 0:
        cards.append(_card(
            "Signal flips tomorrow on a close %s" % ("below" if inm else "above"),
            _n(t2["flip_level"]),
            "%s from the last close; the slow pair makes one day flips rare" % _pct(
                (t2["flip_level"] / tq["last"] - 1) * 100, 0),
        ))
    else:
        cards.append(_card(
            "Signal cannot flip tomorrow",
            "no close does it",
            "the averages are too far apart for any single session to cross them",
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

    charts_html = []
    prefixes = []
    for prefix, title, lines, built in s["charts"]:
        prefixes.append(prefix)
        charts_html.append(_chart_block(prefix, title, lines, built))

    backtest_html = _backtest_section(s.get("backtest") or {}, prefixes)
    dotcom_html = _dotcom_section(s.get("dotcom") or {}, prefixes)

    table_rows = []
    for d, c, a, b in s["chart_series"][-15:][::-1]:
        table_rows.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (d, _n(c), _n(a), _n(b), _pct((a / b - 1) * 100))
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
        explain_html=EXPLAIN,
        cards_html="\n".join(cards),
        charts_html="\n".join(charts_html),
        backtest_html=backtest_html,
        dotcom_html=dotcom_html,
        table_rows="\n".join(table_rows),
        prefixes_json=json.dumps(prefixes),
    )
