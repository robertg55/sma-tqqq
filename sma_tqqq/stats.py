"""Turns raw TQQQ history into the 5/218 signal and every stat the dashboard shows."""

FAST = 5
SLOW = 218
YEAR_SESSIONS = 252
BRAKE_FRACTION = 0.60
CHART_SESSIONS = 250


def rolling_sma(closes, length):
    out = [None] * len(closes)
    acc = 0.0
    for i, c in enumerate(closes):
        acc += c
        if i >= length:
            acc -= closes[i - length]
        if i >= length - 1:
            out[i] = acc / length
    return out


def compute(tqqq_rows, tqqq_quote):
    closes = [r["close"] for r in tqqq_rows]
    dates = [r["date"] for r in tqqq_rows]
    if len(closes) < SLOW + 2:
        raise ValueError("not enough history to compute a %d day average" % SLOW)
    s5 = rolling_sma(closes, FAST)
    s218 = rolling_sma(closes, SLOW)

    last = closes[-1]
    prev = closes[-2]
    in_market = s5[-1] > s218[-1]

    states = [(i, s5[i] > s218[i]) for i in range(len(closes)) if s218[i] is not None]
    crossings_1y = 0
    for k in range(max(1, len(states) - YEAR_SESSIONS), len(states)):
        if states[k][1] != states[k - 1][1]:
            crossings_1y += 1
    days_in_state = 1
    state_since = dates[states[-1][0]]
    for k in range(len(states) - 2, -1, -1):
        if states[k][1] != in_market:
            break
        days_in_state += 1
        state_since = dates[states[k][0]]

    s4 = sum(closes[-(FAST - 1):])
    s217 = sum(closes[-(SLOW - 1):])
    flip_level = (FAST * s217 - SLOW * s4) / (SLOW - FAST)

    live = None
    if tqqq_quote and tqqq_quote.get("price"):
        price = tqqq_quote["price"]
        prov5 = (s4 + price) / FAST
        prov218 = (s217 + price) / SLOW
        live = {
            "price": price,
            "change_pct": tqqq_quote.get("change_pct"),
            "when": tqqq_quote.get("when", ""),
            "market": tqqq_quote.get("market", ""),
            "provisional_sma5": prov5,
            "provisional_sma218": prov218,
            "provisional_signal": "TQQQ" if prov5 > prov218 else "CASH",
            "gap_pct": (prov5 / prov218 - 1) * 100,
        }

    t_peak = max(closes[-YEAR_SESSIONS:])
    t_low = min(closes[-YEAR_SESSIONS:])
    brake_level = BRAKE_FRACTION * t_peak
    tqqq = {
        "last": last,
        "date": dates[-1],
        "day_change_pct": (last / prev - 1) * 100,
        "quote": tqqq_quote,
        "peak_1y": t_peak,
        "low_1y": t_low,
        "drawdown_pct": (last / t_peak - 1) * 100,
        "brake_level": brake_level,
        "above_brake": last > brake_level,
    }

    signal = {
        "signal": "TQQQ" if in_market else "CASH",
        "sma5": s5[-1],
        "sma218": s218[-1],
        "gap_pct": (s5[-1] / s218[-1] - 1) * 100,
        "flip_level": flip_level,
        "crossings_1y": crossings_1y,
        "days_in_state": days_in_state,
        "state_since": state_since,
    }

    first = max(SLOW - 1, len(closes) - CHART_SESSIONS)
    chart_series = [(dates[i], closes[i], s5[i], s218[i]) for i in range(first, len(closes))]

    return {
        "signal": signal["signal"],
        "live": live,
        "tqqq": tqqq,
        "tqqq_5218": signal,
        "chart_series": chart_series,
    }
