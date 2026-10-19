# sma-tqqq

A tiny local web dashboard for a moving average long/flat signal on TQQQ. It runs on your own machine, fetches fresh data from Nasdaq's public API whenever you open the page, and tells you plainly: in market (hold or buy TQQQ) or out (sell, sit in cash). No accounts, no API keys, no database, no third party services beyond the public quote API, and zero Python dependencies.

## The rule it implements

One long/flat signal (TQQQ 5/218): hold TQQQ while its own 5 day average close is above its 218 day average. When the fast line crosses below, sell everything to cash; when it crosses back above, buy back in. The smoothed short side filters one day head fakes, and computing both lines on the leveraged fund itself makes exits more aggressive in bad regimes. Earlier versions also tracked the classic index SMA200 signal; the 5/218 beat it in both the decade backtest and the crash replay, so the dashboard now follows only the 5/218.

Decisions use official closes only; the live quote on the page is informational. The page also shows a secondary "crash brake" level (40 percent below TQQQ's 1 year peak) that deep drawdown backtests favored, the exact TQQQ close that would flip the signal at the next session, and crossing counts.

This is a mechanical indicator, not financial advice.

## Built in backtests

The page carries its own receipts, recomputed from freshly fetched data:

- Ten year backtest: the signal and plain buy and hold start with $10,000 on the first session that has a full 218 day warmup, then trade their rules at official closes through today. Shown as a log scale wealth chart plus final wealth, yearly growth, worst drop, time invested and trade counts.
- Dot-com stress test: the Nasdaq-100's real daily path around its March 2000 peak through the end of 2003 (83% down at the bottom) is replayed with today standing at the exact peak. The whole era series, melt-up year included, is scaled so the peak equals today's prices, which puts both averages where they sat at the top; since scaling moves no crossing, the signal's sell day lands on the same session as in the real tape. TQQQ is simulated at 3 times the daily index move minus the financing costs of that era. A trigger chart shows the melt-up and crash around a today-equals-the-peak divider with the exact sell day, and the text notes how much sooner the sell would come against today's real, much smaller gap. Both strategies enter the crash with their wealth from the ten year backtest.

The 2000 era index and fed funds series come from FRED and are cached in data/ like everything else. The top of the page also has a plain words explainer of TQQQ and the strategy for first time visitors.

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
