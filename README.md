# sma-tqqq

A tiny local web dashboard for a 200 day moving average long/flat signal on TQQQ. It runs on your own machine, fetches fresh data from Nasdaq's public API whenever you open the page, and tells you plainly: in market (hold or buy TQQQ) or out (sell, sit in cash). No accounts, no API keys, no database, no third party services beyond the public quote API, and zero Python dependencies.

## The rules it implements

Two independent long/flat signals are shown side by side, each with its own verdict banner and chart.

Signal 1 (index SMA200): hold TQQQ while the Nasdaq-100 official daily close is above the average of its last 200 official closes. When it closes below, sell everything to cash. When it closes back above, buy back in.

Signal 2 (TQQQ 5/218): hold TQQQ while its own 5 day average close is above its 218 day average, otherwise cash. The smoothed short side trades less often, and computing both lines on the leveraged fund itself makes exits more aggressive in bad regimes.

Decisions use official closes only; the live quote on the page is informational. The page also shows a secondary "crash brake" level (40 percent below TQQQ's 1 year peak) that deep drawdown backtests favored, the exact index level that would flip signal 1 at the next close, crossing counts, and current volatility versus the regimes that make trend filters work.

This is a mechanical indicator, not financial advice.

## Built in backtests

The page carries its own receipts, recomputed from freshly fetched data:

- Ten year backtest: both signals and plain buy and hold start with $10,000 on the first session that has a full 218 day warmup, then trade their rules at official closes through today. Shown as a log scale wealth chart plus final wealth, yearly growth, worst drop, time invested and trade counts.
- Dot-com stress test: the Nasdaq-100's real daily path around its March 2000 peak through the end of 2003 (83% down at the bottom) is replayed with today standing at the exact peak. The whole era series, melt-up year included, is scaled so the peak equals today's prices, which puts every average where it sat at the top; since scaling moves no crossing, each signal's sell day lands on the same session as in the real tape. TQQQ is simulated at 3 times the daily index move minus the financing costs of that era. Two trigger charts show the melt-up and crash around a today-equals-the-peak divider with the exact sell day of each signal, and the text notes how much sooner the sells would come against today's real, much smaller gaps. Each strategy enters the crash with its wealth from the ten year backtest.

The 2000 era index and fed funds series come from FRED and are cached in data/ like everything else. The top of the page also has a plain words explainer of TQQQ and both strategies for first time visitors.

## Quick start

Requires Python 3.10+ and nothing else.

```bash
git clone https://github.com/robertg55/sma-tqqq.git
cd sma-tqqq
python3 -m sma_tqqq
```

Open http://127.0.0.1:8742 in a browser. Every visit uses cached data when it is fresh and refetches when it is not; add `?refresh=1` to force a refetch. The page auto refreshes every 5 minutes.

Poetry users can instead run `poetry install` and then `poetry run sma-tqqq`.

## Start automatically with the PC (Linux, systemd)

```bash
scripts/install-autostart.sh
```

This installs a systemd user service that starts the server at every login and restarts it if it crashes. To have it up even before anyone logs in, additionally run `loginctl enable-linger $USER` once. Remove everything with `scripts/uninstall-autostart.sh`.

## Configuration

Copy `.env.example` to `.env` (gitignored) and edit as needed. Everything is optional; defaults are shown.

| Variable | Default | Meaning |
|---|---|---|
| SMA_TQQQ_HOST | 127.0.0.1 | Bind address. Keep loopback unless you want LAN access. |
| SMA_TQQQ_PORT | 8742 | Port the dashboard serves on. |
| SMA_TQQQ_HISTORY_TTL_MINUTES | 30 | How long fetched daily history is reused before refetching. |
| SMA_TQQQ_QUOTE_TTL_SECONDS | 120 | How long live quotes are reused before refetching. |

There are no secrets in this project; the .env exists so ports and hosts never need to be committed, and so any future sensitive values have a home that git ignores.

## Endpoints

| Path | What it returns |
|---|---|
| `/` | The dashboard. |
| `/api/status` | The same numbers as JSON, for scripts or phone widgets. |
| `/healthz` | `ok`, for monitoring. |

## How data is handled

Fetched history and quotes are cached as JSON under `data/`, which is gitignored along with `.env`; nothing fetched is ever committed. The decade of history used by the backtest refreshes daily, and the fixed 2000 era series from FRED is fetched once and kept. If a fetch fails, the page serves the cached data and shows a warning banner with the age of the last good fetch.

## Project layout

```
sma_tqqq/           the package: config, fetch + cache, stats, chart, html, server
systemd/            service template used by the install script
scripts/            autostart install and uninstall
data/               local cache, created at runtime, never committed
```

## License

MIT
