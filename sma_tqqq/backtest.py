"""Backtests both signals against buy and hold, and replays the dot-com crash."""

from datetime import date, timedelta

from . import stats

START_CASH = 10000.0
WARMUP = max(stats.SMA_LEN, 218)
DOTCOM_PEAK = "2000-03-27"
DOTCOM_END = "2003-12-31"
TQQQ_SPREAD = 0.0060
CHART_POINTS = 520
DC_REAL = 250
DC_FWD = 250


def _align(ndx_rows, tqqq_rows):
    nmap = {r["date"]: r["close"] for r in ndx_rows}
    tmap = {r["date"]: r["close"] for r in tqqq_rows}
    dates = sorted(set(nmap) & set(tmap))
    return dates, [nmap[d] for d in dates], [tmap[d] for d in dates]


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


def decade(ndx_rows, tqqq_rows):
    """Runs both signals and buy and hold from the first fully warmed up session."""
    dates, ndx, tq = _align(ndx_rows, tqqq_rows)
    if len(dates) < WARMUP + 253:
        raise ValueError("only %d aligned sessions, need more history" % len(dates))
    sma200 = stats.rolling_sma(ndx, stats.SMA_LEN)
    s5 = stats.rolling_sma(tq, 5)
    s218 = stats.rolling_sma(tq, 218)
    i0 = WARMUP - 1
    d = dates[i0:]
    t = tq[i0:]
    hold = [True] * len(d)
    sig1 = [ndx[i] > sma200[i] for i in range(i0, len(dates))]
    sig2 = [s5[i] > s218[i] for i in range(i0, len(dates))]
    eq_h = _equity(t, hold, START_CASH)
    eq_1 = _equity(t, sig1, START_CASH)
    eq_2 = _equity(t, sig2, START_CASH)
    return {
        "available": True,
        "start": d[0],
        "end": d[-1],
        "sessions": len(d),
        "start_cash": START_CASH,
        "hold": _summary(d, eq_h, hold),
        "sig1": _summary(d, eq_1, sig1),
        "sig2": _summary(d, eq_2, sig2),
        "series": _thin(d, {"hold": eq_h, "sig1": eq_1, "sig2": eq_2}),
    }


def dotcom(ndx_rows, tqqq_rows, fred_ndx, fred_ff, wealth):
    """Replays the 2000 to 2003 index path from tomorrow, starting from today's wealth."""
    dates, ndx, tq = _align(ndx_rows, tqqq_rows)
    path = [(d, v) for d, v in fred_ndx if DOTCOM_PEAK <= d <= DOTCOM_END]
    if len(path) < 300:
        raise ValueError("dot-com path too short: %d sessions" % len(path))
    rates = {d[:7]: v / 100.0 for d, v in fred_ff}
    last_rate = 0.05
    ndx_ext = list(ndx)
    tq_ext = list(tq)
    for k in range(1, len(path)):
        r = path[k][1] / path[k - 1][1] - 1
        rate = rates.get(path[k][0][:7])
        if rate is None:
            rate = last_rate
        last_rate = rate
        ndx_ext.append(ndx_ext[-1] * (1 + r))
        tq_ext.append(tq_ext[-1] * (1 + 3 * r - (2 * rate + TQQQ_SPREAD) / 252))
    sma200 = stats.rolling_sma(ndx_ext, stats.SMA_LEN)
    s5 = stats.rolling_sma(tq_ext, 5)
    s218 = stats.rolling_sma(tq_ext, 218)
    i0 = len(dates) - 1
    span = range(i0, len(ndx_ext))
    fdates = [dates[-1]]
    cur = date.fromisoformat(dates[-1])
    while len(fdates) < len(path):
        cur += timedelta(days=1)
        if cur.weekday() < 5:
            fdates.append(cur.isoformat())
    hold = [True] * len(fdates)
    sig1 = [ndx_ext[i] > sma200[i] for i in span]
    sig2 = [s5[i] > s218[i] for i in span]
    t = [tq_ext[i] for i in span]
    eq_h = _equity(t, hold, wealth["hold"])
    eq_1 = _equity(t, sig1, wealth["sig1"])
    eq_2 = _equity(t, sig2, wealth["sig2"])
    npath = [ndx_ext[i] for i in span]
    bot = npath.index(min(npath))
    m3 = min(63, len(fdates) - 1)

    def first_sell(pos):
        for k in range(1, len(pos)):
            if pos[k - 1] and not pos[k]:
                return k
        return None

    k1 = first_sell(sig1)
    k2 = first_sell(sig2)
    sig1_exit = None
    if k1 is not None:
        sig1_exit = {"session": k1, "date": fdates[k1],
                     "ndx_drop_pct": (npath[k1] / npath[0] - 1) * 100}
    sig2_exit = None
    if k2 is not None:
        sig2_exit = {"session": k2, "date": fdates[k2],
                     "tqqq_drop_pct": (t[k2] / t[0] - 1) * 100}

    full_dates = dates + fdates[1:]
    w0 = len(dates) - DC_REAL
    w1 = min(len(ndx_ext), len(dates) + DC_FWD)
    win = range(w0, w1)
    price_series = {
        "boundary": DC_REAL - 1,
        "ndx": {
            "dates": [full_dates[i] for i in win],
            "close": [round(ndx_ext[i], 2) for i in win],
            "sma200": [round(sma200[i], 2) for i in win],
        },
        "tqqq": {
            "dates": [full_dates[i] for i in win],
            "close": [round(tq_ext[i], 2) for i in win],
            "sma5": [round(s5[i], 2) for i in win],
            "sma218": [round(s218[i], 2) for i in win],
        },
    }

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
        "replayed_to": DOTCOM_END,
        "bottom_session": bot,
        "ndx_at_bottom_pct": (min(npath) / npath[0] - 1) * 100,
        "ndx_at_end_pct": (npath[-1] / npath[0] - 1) * 100,
        "sig1_exit": sig1_exit,
        "sig2_exit": sig2_exit,
        "hold": snap(eq_h, hold),
        "sig1": snap(eq_1, sig1),
        "sig2": snap(eq_2, sig2),
        "series": _thin(fdates, {"hold": eq_h, "sig1": eq_1, "sig2": eq_2}),
        "price_series": price_series,
    }
