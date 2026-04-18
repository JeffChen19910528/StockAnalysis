# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# Recommended: use the startup scripts (auto-kills old process on port 5000 first)
start.bat          # Windows
./start.sh         # macOS / Linux

# Or start manually (always use venv python directly — do NOT use activate)
venv\Scripts\python.exe app.py          # Windows
venv/bin/python app.py                  # macOS / Linux

# Install / sync packages
venv\Scripts\python.exe -m pip install -r requirements.txt

# Quick smoke test (no server needed)
venv\Scripts\python.exe -c "from app import app; print('OK')"
```

Port defaults to `5000`. Override with `PORT` env var.

> **Windows gotcha**: `pkill` does not work on Windows. Always use `taskkill //F //PID <pid>` or re-run `start.bat` which handles this automatically.

## Environment

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`. Without a key the app runs normally using the rule-based fallback analyser.

## Architecture

Single-file Flask backend (`app.py`) + single-page frontend (`templates/index.html`).

The app supports two markets selectable via the header toggle: **台股 (TW)** and **美股 (US)**.

### API Routes

| Route | Method | Params | Description |
|-------|--------|--------|-------------|
| `/api/search` | GET | `q` | Taiwan stock search (TWSE + TPEX) |
| `/api/search_us` | GET | `q` | US stock search (proxied Yahoo Finance search API) |
| `/api/analyze` | GET | `ticker`, `name`, `market` (`tw`\|`us`) | Fetch + analyse a stock |
| `/api/sectors` | GET | `market` (`tw`\|`us`) | List available sector names for a market |
| `/api/sector_stocks` | GET | `market`, `sector` | Return stocks belonging to a sector |

### Data flow for `/api/analyze`

1. `get_all_tw_stocks()` — fetches and in-process-caches the full stock list from TWSE and TPEX open APIs on first call (Taiwan only)
2. `analyze_stock(ticker, market)` — calls yfinance for 1-year OHLCV + `tk.info`, computes all indicators in-memory, returns a flat dict
3. `generate_recommendation(ticker, name, data, market)` — if `ANTHROPIC_API_KEY` is set, calls Claude (`claude-sonnet-4-6`) requesting a strict JSON response; otherwise falls back to `_rule_based_recommendation(data, market)`
4. Route merges the two dicts and returns JSON (includes `market_type` field)

### Key implementation details

**Stock tickers**: TWSE listed stocks use suffix `.TW`; TPEX OTC stocks use `.TWO`. The `/api/analyze` route auto-retries with the opposite suffix if the first attempt returns no data (Taiwan only). US stocks use the raw symbol (e.g. `AAPL`).

**`dividendYield` from yfinance**:
- Taiwan stocks: already a percentage (e.g. `1.33` means 1.33%). Do **not** multiply by 100.
- US stocks: returned as a decimal (e.g. `0.0133` means 1.33%). **Multiply by 100** — handled via the `market` param in `analyze_stock()`.
- Other ratio fields (`returnOnEquity`, `revenueGrowth`) are always decimals and must be multiplied by 100.

**`safe()` helper**: Converts numpy scalars and `NaN` to plain Python types / `None` before JSON serialisation. Always use it when pulling values from pandas Series into the return dict.

**Chart data**: `analyze_stock()` builds a `chart_data` list of up to 252 dicts (one per trading day) containing pre-computed indicator values. This is consumed directly by Chart.js in the frontend — no second round-trip needed.

**Rule-based scoring** (`_rule_based_recommendation`): Assigns integer points for RSI thresholds, MACD crossover + zero-line position, MA alignment, Bollinger Band breaches, volume-price relationship, dividend yield and P/E. Score ≥ 3 → 買進, ≤ −3 → 賣出, otherwise → 觀望. Thresholds are market-aware: dividend yield threshold is 5% for TW and 2.5% for US; P/E thresholds are 15/30 for TW and 20/35 for US.

**Claude prompt**: Market-aware — uses a Taiwan analyst persona for TW and a US analyst persona for US stocks. Instructs the model to reply with a single JSON object (no markdown fences). The response parser strips a leading ` ```json ` block if the model adds one anyway.

**US stock search**: `search_us_stocks()` proxies the Yahoo Finance search API (`/v1/finance/search`), filters to US exchanges (NMS, NYQ, NGM, etc.), and excludes symbols with dots (foreign listings). Results limited to 15.

**Stock list cache**: `_stock_cache` is a module-level global for Taiwan stocks. It is populated once per process. Restart the server to refresh it.

**Sector data**:
- Taiwan: `_sector_cache_tw` (module-level global, populated on first `/api/sectors?market=tw` call). Fetches from TWSE `t187ap03_L` (listed) and TPEX `mopsfin_t187ap03_O` (OTC). Field `產業別` is used as the sector key. Restart to refresh.
- US: `US_SECTORS` is a hardcoded dict of 11 GICS sectors (科技、通訊服務、醫療保健、金融、非必需消費品、必需消費品、能源、工業、原材料、不動產、公用事業), each with ~10 representative stocks.

### Frontend (`templates/index.html`)

Pure HTML/CSS/JS — no build step. Chart.js is loaded from CDN. All API calls go to the same Flask origin. The page manages four Chart.js instances (`chartPrice`, `chartRsi`, `chartMacd`, `chartVol`); each is destroyed and recreated on every new stock load.

**Market toggle**: Two buttons in the header (🇹🇼 台股 / 🇺🇸 美股). Switching market calls `switchMarket(market)` which:
- Dynamically updates CSS variables `--up` and `--down` (TW: red=up/green=down; US: green=up/red=down)
- Updates the search placeholder and hint text
- Clears current results
- Routes search to `/api/search` or `/api/search_us`
- Passes `market` param to `/api/analyze`
- Resets and reloads the sector pill bar for the new market

**Sector browse panel**: Always-visible pill bar below the search box. On page load `loadSectorPills()` fetches `/api/sectors` and renders clickable pills. Clicking a pill calls `selectSector(sector)` which fetches `/api/sector_stocks` and renders a grid of stock cards below the pills. Clicking the same pill again (or ✕) calls `closeSectorPanel()`. `switchMarket` is monkey-patched to reset the panel and reload pills on market switch.

**Currency display**: NT$ prefix and 元 unit for TW; $ prefix and USD unit for US. Market cap uses 兆/億 for TW and T/B for US.

**Volume bar colours**: Read CSS variables at render time so they respect the current market's colour convention.

## Available Slash Command

`/setup-env` — defined in `.claude/commands/setup-env.md`. Runs the full environment verification flow (Python version, venv, packages, external API connectivity, Flask import check) and outputs a status table.
