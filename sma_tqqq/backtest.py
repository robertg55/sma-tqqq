"""Backtests the signal against buy and hold, and replays the dot-com crash."""

from datetime import date, timedelta

from . import stats

START_CASH = 10000.0
WARMUP = stats.SLOW
DOTCOM_PEAK = "2000-03-27"
TQQQ_SPREAD = 0.0060
CHART_POINTS = 520
DC_REAL = 250
DC_FWD = 250


def _equity(prices, pos, start_cash):
    """pos[i] says whether the money rides the move from close i to close i+1."""
    eq = [start_cash]
    w = start_cash
    for i in range(1, len(prices)):
        if pos[i - 1]:
            w *= prices[i] / prices[i - 1]
        eq.append(w)
    return eq


def _max_drawdown_pct(eq):
    peak, dd = eq[0], 0.0
    for v in eq:
        if v > peak:
            peak = v
        d = v / peak - 1
        if d < dd:
            dd = d
    return dd * 100


def _thin(dates, series_map):
    n = len(dates)
    step = max(1, n // CHART_POINTS)
    idx = list(range(0, n, step))
    if idx[-1] != n - 1:
        idx.append(n - 1)
    out = {"dates": [dates[i] for i in idx]}
    for key, vals in series_map.items():
        out[key] = [round(vals[i], 2) for i in idx]
    return out


def _summary(dates, eq, pos):
    d0 = date.fromisoformat(dates[0])
    d1 = date.fromisoformat(dates[-1])
    years = max((d1 - d0).days / 365.25, 1e-9)
    trades = (1 if pos[0] else 0) + sum(1 for i in range(1, len(pos)) if pos[i] != pos[i - 1])
    return {
        "final": eq[-1],
        "total_return_pct": (eq[-1] / eq[0] - 1) * 100,
        "cagr_pct": ((eq[-1] / eq[0]) ** (1 / years) - 1) * 100,
        "max_drawdown_pct": _max_drawdown_pct(eq),
        "time_in_market_pct": 100.0 * sum(pos) / len(pos),
        "trades": trades,
    }


def decade(tqqq_rows):
    """Runs the signal and buy and hold from the first fully warmed up session."""
    dates = [r["date"] for r in tqqq_rows]
    tq = [r["close"] for r in tqqq_rows]
    if len(dates) < WARMUP + 253:
        raise ValueError("only %d sessions, need more history" % len(dates))
    s5 = stats.rolling_sma(tq, stats.FAST)
    s218 = stats.rolling_sma(tq, stats.SLOW)
    i0 = WARMUP - 1
    d = dates[i0:]
    t = tq[i0:]
    hold = [True] * len(d)
    sig2 = [s5[i] > s218[i] for i in range(i0, len(dates))]
    eq_h = _equity(t, hold, START_CASH)
    eq_2 = _equity(t, sig2, START_CASH)
    return {
        "available": True,
        "start": d[0],
        "end": d[-1],
        "sessions": len(d),
        "start_cash": START_CASH,
        "hold": _summary(d, eq_h, hold),
        "sig2": _summary(d, eq_2, sig2),
        "series": _thin(d, {"hold": eq_h, "sig2": eq_2}),
    }


def dotcom(tqqq_rows, fred_ndx, fred_ff, wealth):
    """Replays 2000 to 2003 with today standing at the exact 2000 peak.

    The era's synthetic TQQQ is scaled so the peak equals today's close, melt-up
    included, so both averages sit where they sat at the top and the sell lands
    on the same session as in the real tape.
    """
    dates = [r["date"] for r in tqqq_rows]
    tq = [r["close"] for r in tqqq_rows]
    hist = list(fred_ndx)
    if len(hist) < 900:
        raise ValueError("dot-com history too short: %d sessions" % len(hist))
    pk = next((i for i, (d, _) in enumerate(hist) if d == DOTCOM_PEAK), None)
    if pk is None:
        pk = max(range(len(hist)), key=lambda i: hist[i][1])
    if pk < WARMUP + DC_REAL or len(hist) - pk < 300:
        raise ValueError("unexpected shape of the dot-com series")
    rates = {d[:7]: v / 100.0 for d, v in fred_ff}
    last_rate = 0.05
    t_hist = [1.0]
    for k in range(1, len(hist)):
        r = hist[k][1] / hist[k - 1][1] - 1
        rate = rates.get(hist[k][0][:7])
        if rate is None:
            rate = last_rate
        last_rate = rate
        t_hist.append(t_hist[-1] * (1 + 3 * r - (2 * rate + TQQQ_SPREAD) / 252))
    tq_s = [v * (tq[-1] / t_hist[pk]) for v in t_hist]
    s5 = stats.rolling_sma(tq_s, stats.FAST)
    s218 = stats.rolling_sma(tq_s, stats.SLOW)

    span = range(pk, len(hist))
    today = date.fromisoformat(dates[-1])
    fdates = [dates[-1]]
    cur = today
    while len(fdates) < len(span):
        cur += timedelta(days=1)
        if cur.weekday() < 5:
            fdates.append(cur.isoformat())
    hold = [True] * len(fdates)
    sig2 = [s5[i] > s218[i] for i in span]
    t = [tq_s[i] for i in span]
    eq_h = _equity(t, hold, wealth["hold"])
    eq_2 = _equity(t, sig2, wealth["sig2"])
    npath = [hist[i][1] for i in span]
    bot = npath.index(min(npath))
    m3 = min(63, len(fdates) - 1)

    def first_sell(pos):
        for k in range(1, len(pos)):
            if pos[k - 1] and not pos[k]:
                return k
        return None

    k2 = first_sell(sig2)
    sig2_exit = None
    if k2 is not None:
        sig2_exit = {"session": k2, "date": fdates[k2],
                     "tqqq_drop_pct": (t[k2] / t[0] - 1) * 100}

    g_tq = list(tq)
    for k in range(pk + 1, min(len(hist), pk + 301)):
        g_tq.append(g_tq[-1] * t_hist[k] / t_hist[k - 1])
    g_s5 = stats.rolling_sma(g_tq, stats.FAST)
    g_s218 = stats.rolling_sma(g_tq, stats.SLOW)
    i0 = len(dates) - 1
    gmax = len(g_tq) - i0
    g2 = next((k for k in range(1, gmax) if g_s5[i0 + k] <= g_s218[i0 + k]), None)

    back = []
    cur = today
    while len(back) < DC_REAL - 1:
        cur -= timedelta(days=1)
        if cur.weekday() < 5:
            back.append(cur.isoformat())
    back.reverse()
    axis_dates = back + fdates[:DC_FWD + 1]
    win = range(pk - (DC_REAL - 1), pk + DC_FWD + 1)
    price_series = {
        "boundary": DC_REAL - 1,
        "tqqq": {
            "dates": axis_dates,
            "close": [round(tq_s[i], 2) for i in win],
            "sma5": [round(s5[i], 2) for i in win],
            "sma218": [round(s218[i], 2) for i in win],
        },
    }

    real5 = sum(tq[-stats.FAST:]) / stats.FAST
    real218 = sum(tq[-stats.SLOW:]) / stats.SLOW

    def snap(eq, pos):
        return {
            "start": eq[0],
            "after_3_months": eq[m3],
            "at_bottom": eq[bot],
            "final": eq[-1],
            "total_return_pct": (eq[-1] / eq[0] - 1) * 100,
            "max_drawdown_pct": _max_drawdown_pct(eq),
            "trades": sum(1 for i in range(1, len(pos)) if pos[i] != pos[i - 1]),
        }

    return {
        "available": True,
        "sessions": len(fdates) - 1,
        "replayed_from": DOTCOM_PEAK,
        "replayed_to": hist[-1][0],
        "bottom_session": bot,
        "ndx_at_bottom_pct": (min(npath) / npath[0] - 1) * 100,
        "ndx_at_end_pct": (npath[-1] / npath[0] - 1) * 100,
        "peak_gap_pct": (s5[pk] / s218[pk] - 1) * 100,
        "today_gap_pct": (real5 / real218 - 1) * 100,
        "sig2_exit": sig2_exit,
        "today_gap_exits": {"sig2_day": g2},
        "hold": snap(eq_h, hold),
        "sig2": snap(eq_2, sig2),
        "series": _thin(fdates, {"hold": eq_h, "sig2": eq_2}),
        "price_series": price_series,
    }
