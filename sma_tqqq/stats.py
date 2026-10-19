"""Turns raw price history into the signal and every stat the dashboard shows."""

import math
from statistics import pstdev

SMA_LEN = 200
YEAR_SESSIONS = 252
BRAKE_FRACTION = 0.60
BAND_FRACTION = 0.98
CHART_SESSIONS = 250


def rolling_sma(closes, length=SMA_LEN):
    out = [None] * len(closes)
    acc = 0.0
    for i, c in enumerate(closes):
        acc += c
        if i >= length:
            acc -= closes[i - length]
        if i >= length - 1:
            out[i] = acc / length
    return out


def compute(ndx_rows, tqqq_rows, ndx_quote, tqqq_quote):
    closes = [r["close"] for r in ndx_rows]
    dates = [r["date"] for r in ndx_rows]
    if len(closes) < SMA_LEN + 2:
        raise ValueError("not enough history to compute a %d day average" % SMA_LEN)
    smas = rolling_sma(closes)

    last = closes[-1]
    prev = closes[-2]
    sma = smas[-1]
    in_market = last > sma
    gap_pct = (last / sma - 1) * 100
    flip_level = sum(closes[-(SMA_LEN - 1):]) / (SMA_LEN - 1)
    band_level = BAND_FRACTION * sma

    states = [(i, closes[i] > smas[i]) for i in range(len(closes)) if smas[i] is not None]
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

    live = None
    if ndx_quote and ndx_quote.get("price"):
        price = ndx_quote["price"]
        prov_sma = (sum(closes[-(SMA_LEN - 1):]) + price) / SMA_LEN
        live = {
            "price": price,
            "change_pct": ndx_quote.get("change_pct"),
            "when": ndx_quote.get("when", ""),
            "market": ndx_quote.get("market", ""),
            "provisional_sma": prov_sma,
            "provisional_signal": "TQQQ" if price > prov_sma else "CASH",
            "gap_pct": (price / prov_sma - 1) * 100,
        }

    rets = [closes[i] / closes[i - 1] - 1 for i in range(len(closes) - 20, len(closes))]
    vol20 = pstdev(rets) * math.sqrt(252) * 100

    t_closes = [r["close"] for r in tqqq_rows]
    t_last = t_closes[-1]
    t_prev = t_closes[-2]
    t_peak = max(t_closes[-YEAR_SESSIONS:])
    t_low = min(t_closes[-YEAR_SESSIONS:])
    brake_level = BRAKE_FRACTION * t_peak
    tqqq = {
        "last": t_last,
        "date": tqqq_rows[-1]["date"],
        "day_change_pct": (t_last / t_prev - 1) * 100,
        "quote": tqqq_quote,
        "peak_1y": t_peak,
        "low_1y": t_low,
        "drawdown_pct": (t_last / t_peak - 1) * 100,
        "brake_level": brake_level,
        "above_brake": t_last > brake_level,
    }

    t_dates = [r["date"] for r in tqqq_rows]
    s5 = rolling_sma(t_closes, 5)
    s218 = rolling_sma(t_closes, 218)
    t_states = [(i, s5[i] > s218[i]) for i in range(len(t_closes)) if s218[i] is not None]
    x_1y = 0
    for k in range(max(1, len(t_states) - YEAR_SESSIONS), len(t_states)):
        if t_states[k][1] != t_states[k - 1][1]:
            x_1y += 1
    in5218 = t_states[-1][1]
    days5218 = 1
    since5218 = t_dates[t_states[-1][0]]
    for k in range(len(t_states) - 2, -1, -1):
        if t_states[k][1] != in5218:
            break
        days5218 += 1
        since5218 = t_dates[t_states[k][0]]
    tqqq_5218 = {
        "signal": "TQQQ" if in5218 else "CASH",
        "sma5": s5[-1],
        "sma218": s218[-1],
        "gap_pct": (s5[-1] / s218[-1] - 1) * 100,
        "crossings_1y": x_1y,
        "days_in_state": days5218,
        "state_since": since5218,
    }
    first2 = max(217, len(t_closes) - CHART_SESSIONS)
    chart2 = [(t_dates[i], t_closes[i], s5[i], s218[i]) for i in range(first2, len(t_closes))]

    first_chart = max(SMA_LEN - 1, len(closes) - CHART_SESSIONS)
    chart_series = [(dates[i], closes[i], smas[i]) for i in range(first_chart, len(closes))]

    return {
        "signal": "TQQQ" if in_market else "CASH",
        "ndx": {
            "close": last,
            "date": dates[-1],
            "day_change_pct": (last / prev - 1) * 100,
            "sma200": sma,
            "gap_pct": gap_pct,
            "flip_level": flip_level,
            "band_level": band_level,
            "crossings_1y": crossings_1y,
            "days_in_state": days_in_state,
            "state_since": state_since,
            "vol20_pct": vol20,
        },
        "live": live,
        "tqqq": tqqq,
        "tqqq_5218": tqqq_5218,
        "chart_series": chart_series,
        "chart2_series": chart2,
    }
