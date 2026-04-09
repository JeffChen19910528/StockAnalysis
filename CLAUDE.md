# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# Start the server (always use venv python directly — do NOT use activate)
venv\Scripts\python.exe app.py          # Windows
venv/bin/python app.py                  # macOS / Linux

# Install / sync packages
venv\Scripts\python.exe -m pip install -r requirements.txt

# Quick smoke test (no server needed)
venv\Scripts\python.exe -c "from app import app; print('OK')"
```

Port defaults to `5000`. Override with `PORT` env var.

## Environment

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`. Without a key the app runs normally using the rule-based fallback analyser.

## Architecture

Single-file Flask backend (`app.py`) + single-page frontend (`templates/index.html`).

### Data flow for `/api/analyze`

1. `get_all_tw_stocks()` — fetches and in-process-caches the full stock list from TWSE and TPEX open APIs on first call
2. `analyze_stock(ticker)` — calls yfinance for 1-year OHLCV + `tk.info`, computes all indicators in-memory, returns a flat dict
3. `generate_recommendation()` — if `ANTHROPIC_API_KEY` is set, calls Claude (`claude-sonnet-4-6`) requesting a strict JSON response; otherwise falls back to `_rule_based_recommendation()`
4. Route merges the two dicts and returns JSON

### Key implementation details

**Stock tickers**: TWSE listed stocks use suffix `.TW`; TPEX OTC stocks use `.TWO`. The `/api/analyze` route auto-retries with the opposite suffix if the first attempt returns no data.

**`dividendYield` from yfinance**: For Taiwan stocks yfinance returns this field already as a percentage (e.g. `1.33` means 1.33%). Do **not** multiply by 100. Other ratio fields (`returnOnEquity`, `revenueGrowth`) are returned as decimals and must be multiplied by 100.

**`safe()` helper**: Converts numpy scalars and `NaN` to plain Python types / `None` before JSON serialisation. Always use it when pulling values from pandas Series into the return dict.

**Chart data**: `analyze_stock()` builds a `chart_data` list of up to 252 dicts (one per trading day) containing pre-computed indicator values. This is consumed directly by Chart.js in the frontend — no second round-trip needed.

**Rule-based scoring** (`_rule_based_recommendation`): Assigns integer points for RSI thresholds, MACD crossover + zero-line position, MA alignment, Bollinger Band breaches, volume-price relationship, dividend yield and P/E. Score ≥ 3 → 買進, ≤ −3 → 賣出, otherwise → 觀望.

**Claude prompt**: Instructs the model to reply with a single JSON object (no markdown fences). The response parser strips a leading ```` ```json ```` block if the model adds one anyway.

**Stock list cache**: `_stock_cache` is a module-level global. It is populated once per process. Restart the server to refresh it.

### Frontend (`templates/index.html`)

Pure HTML/CSS/JS — no build step. Chart.js is loaded from CDN. All API calls go to the same Flask origin. The page manages four Chart.js instances (`chartPrice`, `chartRsi`, `chartMacd`, `chartVol`); each is destroyed and recreated on every new stock load.

Taiwan convention: **red = price up, green = price down** (opposite of Western markets). This is reflected in the CSS variables `--up: #dc2626` and `--down: #16a34a` and in volume bar colouring.

## Available Slash Command

`/setup-env` — defined in `.claude/commands/setup-env.md`. Runs the full environment verification flow (Python version, venv, packages, external API connectivity, Flask import check) and outputs a status table.
