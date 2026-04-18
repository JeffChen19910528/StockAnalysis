import os
import json
import requests
import urllib3
import numpy as np

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import pandas as pd
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic
from flask import Flask, render_template, request, jsonify

load_dotenv()

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False  # 讓 JSON 直接顯示中文（Flask 2.x 以上）
app.json.ensure_ascii = False
anthropic_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

# ─── 台股清單快取 ────────────────────────────────────────────────────────────────
_stock_cache = None
_sector_cache_tw = None  # dict: {sector_name: [{code, name, ticker, market}]}

# ─── 美股預設產業清單 ─────────────────────────────────────────────────────────────
US_SECTORS = {
    "科技": [
        {"code": "AAPL", "name": "Apple",        "ticker": "AAPL", "market": "股票"},
        {"code": "MSFT", "name": "Microsoft",     "ticker": "MSFT", "market": "股票"},
        {"code": "NVDA", "name": "NVIDIA",        "ticker": "NVDA", "market": "股票"},
        {"code": "AVGO", "name": "Broadcom",      "ticker": "AVGO", "market": "股票"},
        {"code": "ORCL", "name": "Oracle",        "ticker": "ORCL", "market": "股票"},
        {"code": "AMD",  "name": "AMD",           "ticker": "AMD",  "market": "股票"},
        {"code": "INTC", "name": "Intel",         "ticker": "INTC", "market": "股票"},
        {"code": "CRM",  "name": "Salesforce",    "ticker": "CRM",  "market": "股票"},
        {"code": "NOW",  "name": "ServiceNow",    "ticker": "NOW",  "market": "股票"},
        {"code": "PLTR", "name": "Palantir",      "ticker": "PLTR", "market": "股票"},
    ],
    "通訊服務": [
        {"code": "GOOGL","name": "Alphabet",      "ticker": "GOOGL","market": "股票"},
        {"code": "META", "name": "Meta",          "ticker": "META", "market": "股票"},
        {"code": "NFLX", "name": "Netflix",       "ticker": "NFLX", "market": "股票"},
        {"code": "DIS",  "name": "Disney",        "ticker": "DIS",  "market": "股票"},
        {"code": "CMCSA","name": "Comcast",       "ticker": "CMCSA","market": "股票"},
        {"code": "T",    "name": "AT&T",          "ticker": "T",    "market": "股票"},
        {"code": "VZ",   "name": "Verizon",       "ticker": "VZ",   "market": "股票"},
        {"code": "SNAP", "name": "Snap",          "ticker": "SNAP", "market": "股票"},
        {"code": "RBLX", "name": "Roblox",        "ticker": "RBLX", "market": "股票"},
        {"code": "SPOT", "name": "Spotify",       "ticker": "SPOT", "market": "股票"},
    ],
    "醫療保健": [
        {"code": "UNH",  "name": "UnitedHealth",  "ticker": "UNH",  "market": "股票"},
        {"code": "LLY",  "name": "Eli Lilly",     "ticker": "LLY",  "market": "股票"},
        {"code": "JNJ",  "name": "J&J",           "ticker": "JNJ",  "market": "股票"},
        {"code": "MRK",  "name": "Merck",         "ticker": "MRK",  "market": "股票"},
        {"code": "ABBV", "name": "AbbVie",        "ticker": "ABBV", "market": "股票"},
        {"code": "TMO",  "name": "Thermo Fisher", "ticker": "TMO",  "market": "股票"},
        {"code": "ABT",  "name": "Abbott",        "ticker": "ABT",  "market": "股票"},
        {"code": "DHR",  "name": "Danaher",       "ticker": "DHR",  "market": "股票"},
        {"code": "BMY",  "name": "Bristol-Myers", "ticker": "BMY",  "market": "股票"},
        {"code": "PFE",  "name": "Pfizer",        "ticker": "PFE",  "market": "股票"},
    ],
    "金融": [
        {"code": "JPM",  "name": "JPMorgan",      "ticker": "JPM",  "market": "股票"},
        {"code": "BAC",  "name": "Bank of America","ticker": "BAC", "market": "股票"},
        {"code": "WFC",  "name": "Wells Fargo",   "ticker": "WFC",  "market": "股票"},
        {"code": "GS",   "name": "Goldman Sachs", "ticker": "GS",   "market": "股票"},
        {"code": "MS",   "name": "Morgan Stanley","ticker": "MS",   "market": "股票"},
        {"code": "BLK",  "name": "BlackRock",     "ticker": "BLK",  "market": "股票"},
        {"code": "V",    "name": "Visa",          "ticker": "V",    "market": "股票"},
        {"code": "MA",   "name": "Mastercard",    "ticker": "MA",   "market": "股票"},
        {"code": "AXP",  "name": "Amex",          "ticker": "AXP",  "market": "股票"},
        {"code": "C",    "name": "Citigroup",     "ticker": "C",    "market": "股票"},
    ],
    "非必需消費品": [
        {"code": "AMZN", "name": "Amazon",        "ticker": "AMZN", "market": "股票"},
        {"code": "TSLA", "name": "Tesla",         "ticker": "TSLA", "market": "股票"},
        {"code": "HD",   "name": "Home Depot",    "ticker": "HD",   "market": "股票"},
        {"code": "MCD",  "name": "McDonald's",    "ticker": "MCD",  "market": "股票"},
        {"code": "NKE",  "name": "Nike",          "ticker": "NKE",  "market": "股票"},
        {"code": "SBUX", "name": "Starbucks",     "ticker": "SBUX", "market": "股票"},
        {"code": "TGT",  "name": "Target",        "ticker": "TGT",  "market": "股票"},
        {"code": "LOW",  "name": "Lowe's",        "ticker": "LOW",  "market": "股票"},
        {"code": "BKNG", "name": "Booking",       "ticker": "BKNG", "market": "股票"},
        {"code": "ABNB", "name": "Airbnb",        "ticker": "ABNB", "market": "股票"},
    ],
    "必需消費品": [
        {"code": "PG",   "name": "Procter & Gamble","ticker": "PG", "market": "股票"},
        {"code": "KO",   "name": "Coca-Cola",     "ticker": "KO",   "market": "股票"},
        {"code": "PEP",  "name": "PepsiCo",       "ticker": "PEP",  "market": "股票"},
        {"code": "WMT",  "name": "Walmart",       "ticker": "WMT",  "market": "股票"},
        {"code": "COST", "name": "Costco",        "ticker": "COST", "market": "股票"},
        {"code": "PM",   "name": "Philip Morris", "ticker": "PM",   "market": "股票"},
        {"code": "MDLZ", "name": "Mondelez",      "ticker": "MDLZ", "market": "股票"},
        {"code": "CL",   "name": "Colgate",       "ticker": "CL",   "market": "股票"},
        {"code": "GIS",  "name": "General Mills", "ticker": "GIS",  "market": "股票"},
        {"code": "KR",   "name": "Kroger",        "ticker": "KR",   "market": "股票"},
    ],
    "能源": [
        {"code": "XOM",  "name": "ExxonMobil",    "ticker": "XOM",  "market": "股票"},
        {"code": "CVX",  "name": "Chevron",       "ticker": "CVX",  "market": "股票"},
        {"code": "COP",  "name": "ConocoPhillips","ticker": "COP",  "market": "股票"},
        {"code": "EOG",  "name": "EOG Resources", "ticker": "EOG",  "market": "股票"},
        {"code": "SLB",  "name": "SLB",           "ticker": "SLB",  "market": "股票"},
        {"code": "OXY",  "name": "Occidental",    "ticker": "OXY",  "market": "股票"},
        {"code": "VLO",  "name": "Valero",        "ticker": "VLO",  "market": "股票"},
        {"code": "MPC",  "name": "Marathon",      "ticker": "MPC",  "market": "股票"},
        {"code": "PSX",  "name": "Phillips 66",   "ticker": "PSX",  "market": "股票"},
        {"code": "HAL",  "name": "Halliburton",   "ticker": "HAL",  "market": "股票"},
    ],
    "工業": [
        {"code": "BA",   "name": "Boeing",        "ticker": "BA",   "market": "股票"},
        {"code": "CAT",  "name": "Caterpillar",   "ticker": "CAT",  "market": "股票"},
        {"code": "GE",   "name": "GE",            "ticker": "GE",   "market": "股票"},
        {"code": "HON",  "name": "Honeywell",     "ticker": "HON",  "market": "股票"},
        {"code": "UPS",  "name": "UPS",           "ticker": "UPS",  "market": "股票"},
        {"code": "RTX",  "name": "RTX",           "ticker": "RTX",  "market": "股票"},
        {"code": "MMM",  "name": "3M",            "ticker": "MMM",  "market": "股票"},
        {"code": "DE",   "name": "Deere",         "ticker": "DE",   "market": "股票"},
        {"code": "LMT",  "name": "Lockheed",      "ticker": "LMT",  "market": "股票"},
        {"code": "FDX",  "name": "FedEx",         "ticker": "FDX",  "market": "股票"},
    ],
    "原材料": [
        {"code": "LIN",  "name": "Linde",         "ticker": "LIN",  "market": "股票"},
        {"code": "APD",  "name": "Air Products",  "ticker": "APD",  "market": "股票"},
        {"code": "ECL",  "name": "Ecolab",        "ticker": "ECL",  "market": "股票"},
        {"code": "NEM",  "name": "Newmont",       "ticker": "NEM",  "market": "股票"},
        {"code": "FCX",  "name": "Freeport",      "ticker": "FCX",  "market": "股票"},
        {"code": "NUE",  "name": "Nucor",         "ticker": "NUE",  "market": "股票"},
        {"code": "PPG",  "name": "PPG Ind.",      "ticker": "PPG",  "market": "股票"},
        {"code": "VMC",  "name": "Vulcan",        "ticker": "VMC",  "market": "股票"},
        {"code": "MLM",  "name": "Martin Marietta","ticker": "MLM", "market": "股票"},
        {"code": "DOW",  "name": "Dow Inc.",      "ticker": "DOW",  "market": "股票"},
    ],
    "不動產": [
        {"code": "AMT",  "name": "American Tower","ticker": "AMT",  "market": "股票"},
        {"code": "PLD",  "name": "Prologis",      "ticker": "PLD",  "market": "股票"},
        {"code": "CCI",  "name": "Crown Castle",  "ticker": "CCI",  "market": "股票"},
        {"code": "EQIX", "name": "Equinix",       "ticker": "EQIX", "market": "股票"},
        {"code": "DLR",  "name": "Digital Realty","ticker": "DLR",  "market": "股票"},
        {"code": "PSA",  "name": "Public Storage","ticker": "PSA",  "market": "股票"},
        {"code": "O",    "name": "Realty Income", "ticker": "O",    "market": "股票"},
        {"code": "WELL", "name": "Welltower",     "ticker": "WELL", "market": "股票"},
        {"code": "SPG",  "name": "Simon Property","ticker": "SPG",  "market": "股票"},
        {"code": "AVB",  "name": "AvalonBay",     "ticker": "AVB",  "market": "股票"},
    ],
    "公用事業": [
        {"code": "NEE",  "name": "NextEra",       "ticker": "NEE",  "market": "股票"},
        {"code": "DUK",  "name": "Duke Energy",   "ticker": "DUK",  "market": "股票"},
        {"code": "SO",   "name": "Southern Co.",  "ticker": "SO",   "market": "股票"},
        {"code": "D",    "name": "Dominion",      "ticker": "D",    "market": "股票"},
        {"code": "EXC",  "name": "Exelon",        "ticker": "EXC",  "market": "股票"},
        {"code": "AEP",  "name": "Am. Elec. Pwr", "ticker": "AEP",  "market": "股票"},
        {"code": "SRE",  "name": "Sempra",        "ticker": "SRE",  "market": "股票"},
        {"code": "XEL",  "name": "Xcel Energy",   "ticker": "XEL",  "market": "股票"},
        {"code": "ED",   "name": "Con Edison",    "ticker": "ED",   "market": "股票"},
        {"code": "ETR",  "name": "Entergy",       "ticker": "ETR",  "market": "股票"},
    ],
}

def get_tw_sector_cache():
    """回傳 {產業別: [{code, name, ticker, market}]} 的字典，使用 TWSE opendata 取得"""
    global _sector_cache_tw
    if _sector_cache_tw is not None:
        return _sector_cache_tw

    result = {}
    headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(
            "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
            timeout=15, headers=headers, verify=False
        )
        if r.status_code == 200 and "application/json" in r.headers.get("Content-Type", ""):
            for item in r.json():
                code   = item.get("公司代號", "").strip()
                name   = item.get("公司名稱", "").strip()
                sector = item.get("產業別", "其他").strip() or "其他"
                if code and name and code.isdigit():
                    result.setdefault(sector, []).append(
                        {"code": code, "name": name, "ticker": f"{code}.TW", "market": "上市"}
                    )
    except Exception as e:
        print(f"[TW sector TWSE error] {e}")

    try:
        r = requests.get(
            "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O",
            timeout=15, headers=headers, verify=False
        )
        if r.status_code == 200 and "application/json" in r.headers.get("Content-Type", ""):
            for item in r.json():
                code   = item.get("公司代號", "").strip()
                name   = item.get("公司名稱", "").strip()
                sector = item.get("產業別", "其他").strip() or "其他"
                if code and name and code.isdigit():
                    result.setdefault(sector, []).append(
                        {"code": code, "name": name, "ticker": f"{code}.TWO", "market": "上櫃"}
                    )
    except Exception as e:
        print(f"[TW sector TPEX error] {e}")

    _sector_cache_tw = result
    return result


def get_all_tw_stocks():
    global _stock_cache
    if _stock_cache:
        return _stock_cache

    stocks = []
    headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

    # 上市公司（TWSE） — STOCK_DAY_ALL 包含代碼+名稱
    try:
        r = requests.get(
            "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
            timeout=12, headers=headers, verify=False
        )
        if r.status_code == 200 and "application/json" in r.headers.get("Content-Type", ""):
            for item in r.json():
                code = item.get("Code", "").strip()
                name = item.get("Name", "").strip()
                if code and name and code.isdigit():
                    stocks.append({"code": code, "name": name, "market": "上市", "ticker": f"{code}.TW"})
    except Exception as e:
        print(f"[TWSE list error] {e}")

    # 上櫃公司（TPEX） — tpex_mainboard_quotes
    try:
        r = requests.get(
            "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes",
            timeout=12, headers=headers, verify=False
        )
        if r.status_code == 200 and "application/json" in r.headers.get("Content-Type", ""):
            for item in r.json():
                code = item.get("SecuritiesCompanyCode", "").strip()
                name = item.get("CompanyName", "").strip()
                if code and name and code.isdigit():
                    stocks.append({"code": code, "name": name, "market": "上櫃", "ticker": f"{code}.TWO"})
    except Exception as e:
        print(f"[TPEX list error] {e}")

    _stock_cache = stocks
    return stocks


def search_stocks(keyword: str):
    keyword = keyword.strip()
    if not keyword:
        return []
    stocks = get_all_tw_stocks()

    def relevance(s):
        code, name = s["code"], s["name"]
        if code == keyword or name == keyword:
            return 0  # 完全符合
        if code.startswith(keyword) or name.startswith(keyword):
            return 1  # 前綴符合
        return 2      # 包含

    results = [s for s in stocks if keyword in s["code"] or keyword in s["name"]]
    results.sort(key=relevance)
    return results[:20]


# ─── 美股搜尋（透過 Yahoo Finance Search API）────────────────────────────────────

def search_us_stocks(keyword: str):
    keyword = keyword.strip()
    if not keyword:
        return []
    US_EXCHANGES = {"NMS", "NYQ", "NGM", "PCX", "ASE", "BTS", "NCM", "NAS", "NYSE MKT"}
    try:
        r = requests.get(
            "https://query1.finance.yahoo.com/v1/finance/search",
            params={"q": keyword, "quotesCount": 20, "newsCount": 0},
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=10,
        )
        if r.status_code == 200:
            results = []
            for q in r.json().get("quotes", []):
                if q.get("quoteType") not in ("EQUITY", "ETF"):
                    continue
                if q.get("exchange", "") not in US_EXCHANGES:
                    continue
                symbol = q.get("symbol", "")
                if not symbol or "." in symbol:
                    continue
                results.append({
                    "code":   symbol,
                    "name":   q.get("longname") or q.get("shortname", symbol),
                    "market": "ETF" if q.get("quoteType") == "ETF" else "股票",
                    "ticker": symbol,
                })
            return results[:15]
    except Exception as e:
        print(f"[US search error] {e}")
    return []


# ─── 技術指標計算 ────────────────────────────────────────────────────────────────

def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_f = series.ewm(span=fast, adjust=False).mean()
    ema_s = series.ewm(span=slow, adjust=False).mean()
    macd = ema_f - ema_s
    sig = macd.ewm(span=signal, adjust=False).mean()
    return macd, sig, macd - sig


def calc_bollinger(series: pd.Series, period=20, k=2):
    ma = series.rolling(period).mean()
    std = series.rolling(period).std()
    return ma + k * std, ma, ma - k * std


def safe(val):
    """將 numpy/nan 轉為 Python 原生型別，nan -> None"""
    if val is None:
        return None
    if isinstance(val, (float, np.floating)):
        return None if np.isnan(val) else round(float(val), 4)
    if isinstance(val, (int, np.integer)):
        return int(val)
    return val


# ─── 股票分析主邏輯 ──────────────────────────────────────────────────────────────

def analyze_stock(ticker: str, market: str = "tw"):
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="1y", auto_adjust=True)
        if hist.empty or len(hist) < 5:
            return None

        info = {}
        try:
            info = tk.info or {}
        except Exception:
            pass

        close = hist["Close"]
        current_price = float(close.iloc[-1])
        prev_price = float(close.iloc[-2])
        price_change = current_price - prev_price
        price_change_pct = price_change / prev_price * 100

        # 均線
        ma5  = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()

        # RSI
        rsi = calc_rsi(close)

        # MACD
        macd_line, signal_line, histogram = calc_macd(close)

        # 布林通道
        bb_upper, bb_mid, bb_lower = calc_bollinger(close)

        # 支撐 / 壓力（近60根）
        recent = close.tail(60)
        support    = float(recent.rolling(20).min().iloc[-1])
        resistance = float(recent.rolling(20).max().iloc[-1])

        # 成交量（近5日均量）
        vol_avg5 = float(hist["Volume"].tail(5).mean())
        vol_today = float(hist["Volume"].iloc[-1])

        # 基本面
        pe = info.get("trailingPE")
        pb = info.get("priceToBook")
        roe = info.get("returnOnEquity")
        div_yield = info.get("dividendYield")
        market_cap = info.get("marketCap")
        eps = info.get("trailingEps")
        revenue_growth = info.get("revenueGrowth")

        # 股利歷史
        div_history = []
        try:
            divs = tk.dividends
            if divs is not None and not divs.empty:
                for dt, amt in divs.tail(8).items():
                    div_history.append({"date": dt.strftime("%Y-%m-%d"), "amount": round(float(amt), 2)})
        except Exception:
            pass

        # 圖表資料（最多252個交易日）
        chart_data = []
        chart_hist = hist.tail(252)
        for dt, row in chart_hist.iterrows():
            idx = chart_hist.index.get_loc(dt)
            chart_data.append({
                "date":   dt.strftime("%Y-%m-%d"),
                "close":  safe(row["Close"]),
                "ma5":    safe(ma5.iloc[hist.index.get_loc(dt)]) if hist.index.get_loc(dt) < len(ma5) else None,
                "ma20":   safe(ma20.iloc[hist.index.get_loc(dt)]) if hist.index.get_loc(dt) < len(ma20) else None,
                "ma60":   safe(ma60.iloc[hist.index.get_loc(dt)]) if hist.index.get_loc(dt) < len(ma60) else None,
                "volume": safe(row["Volume"]),
                "rsi":    safe(rsi.iloc[hist.index.get_loc(dt)]),
                "macd":   safe(macd_line.iloc[hist.index.get_loc(dt)]),
                "signal": safe(signal_line.iloc[hist.index.get_loc(dt)]),
                "histo":  safe(histogram.iloc[hist.index.get_loc(dt)]),
                "bb_upper": safe(bb_upper.iloc[hist.index.get_loc(dt)]),
                "bb_lower": safe(bb_lower.iloc[hist.index.get_loc(dt)]),
            })

        return {
            "current_price":    round(current_price, 2),
            "price_change":     round(price_change, 2),
            "price_change_pct": round(price_change_pct, 2),
            "rsi":       safe(rsi.iloc[-1]),
            "macd":      safe(macd_line.iloc[-1]),
            "macd_signal": safe(signal_line.iloc[-1]),
            "macd_histo":  safe(histogram.iloc[-1]),
            "ma5":  safe(ma5.iloc[-1]),
            "ma10": safe(ma10.iloc[-1]),
            "ma20": safe(ma20.iloc[-1]),
            "ma60": safe(ma60.iloc[-1]),
            "bb_upper": safe(bb_upper.iloc[-1]),
            "bb_lower": safe(bb_lower.iloc[-1]),
            "support":    round(support, 2),
            "resistance": round(resistance, 2),
            "vol_today":  int(vol_today),
            "vol_avg5":   int(vol_avg5),
            "pe_ratio":   safe(pe),
            "pb_ratio":   safe(pb),
            "roe":        round(roe * 100, 2) if roe else None,
            # yfinance 台股已為百分比；美股為小數，需乘以 100
            "div_yield":  round(div_yield * (1 if market == "tw" else 100), 2) if div_yield else None,
            "market_cap": market_cap,
            "eps":        safe(eps),
            "revenue_growth": round(revenue_growth * 100, 2) if revenue_growth else None,
            "div_history": div_history,
            "chart_data":  chart_data,
        }

    except Exception as e:
        print(f"[analyze_stock error] {ticker}: {e}")
        return None


# ─── Claude AI 投資建議 ──────────────────────────────────────────────────────────

def generate_recommendation(ticker: str, name: str, data: dict, market: str = "tw") -> dict:
    """回傳 { text, action, buy_low, buy_high, sell_low, sell_high }"""

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_api_key_here":
        return _rule_based_recommendation(data, market)

    currency = "元" if market == "tw" else "USD"
    if market == "us":
        analyst_role = "你是一位擁有20年經驗的美國股市專業分析師，熟悉 NYSE / Nasdaq 市場。"
    else:
        analyst_role = "你是一位擁有20年經驗的台灣股市專業分析師。"

    prompt = f"""{analyst_role}請根據以下 **{name}（{ticker}）** 的即時數據，提供一份嚴謹、具體的投資分析報告。

## 【價格資訊】
- 現價：{data['current_price']} {currency}
- 今日漲跌：{data['price_change']:+.2f} {currency}（{data['price_change_pct']:+.2f}%）

## 【技術指標】
| 指標 | 數值 |
|------|------|
| RSI(14) | {data['rsi']} |
| MACD | {data['macd']} |
| MACD Signal | {data['macd_signal']} |
| MACD Histogram | {data['macd_histo']} |
| MA5 | {data['ma5']} |
| MA20 | {data['ma20']} |
| MA60 | {data['ma60']} |
| 布林上軌 | {data['bb_upper']} |
| 布林下軌 | {data['bb_lower']} |
| 近期支撐位 | {data['support']} |
| 近期壓力位 | {data['resistance']} |
| 今日成交量 | {data['vol_today']:,} |
| 5日均量 | {data['vol_avg5']:,} |

## 【基本面】
| 項目 | 數值 |
|------|------|
| 本益比 P/E | {data['pe_ratio'] or 'N/A'} |
| 股價淨值比 P/B | {data['pb_ratio'] or 'N/A'} |
| ROE | {data['roe'] or 'N/A'}% |
| 殖利率 | {data['div_yield'] or 'N/A'}% |
| EPS | {data['eps'] or 'N/A'} |
| 營收成長率 | {data['revenue_growth'] or 'N/A'}% |

---

請嚴格按照以下 JSON 格式回覆，不要有任何 JSON 以外的文字：

{{
  "action": "買進" 或 "賣出" 或 "觀望",
  "summary": "整體評估（60字內）",
  "technical_analysis": "技術面詳細分析（100-150字，涵蓋RSI、MACD、均線、布林通道、量價關係）",
  "fundamental_analysis": "基本面詳細分析（80-120字，涵蓋估值、獲利能力、股利）",
  "recommendation": "明確投資建議與理由（80字內）",
  "buy_low": 若action為買進，填寫建議買進區間下限價格（純數字），否則填 null,
  "buy_high": 若action為買進，填寫建議買進區間上限價格（純數字），否則填 null,
  "stop_loss": 若action為買進，填寫停損價格（純數字），否則填 null,
  "sell_low": 若action為賣出，填寫建議賣出區間下限價格（純數字），否則填 null,
  "sell_high": 若action為賣出，填寫建議賣出區間上限價格（純數字），否則填 null,
  "take_profit": 若action為賣出，填寫停利目標價格（純數字），否則填 null,
  "wait_condition": 若action為觀望，說明需要等待哪些條件才進場（50字內），否則填 null,
  "risk_warning": "風險提示（30字內）"
}}

注意：價格區間必須合理，基於技術分析的支撐壓力位計算，請務必給出具體數字。"""

    try:
        msg = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = msg.content[0].text.strip()
        # 嘗試剝離 markdown code block
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        return result
    except Exception as e:
        print(f"[Claude API error] {e}")
        return _rule_based_recommendation(data, market)


def _rule_based_recommendation(data: dict, market: str = "tw") -> dict:
    """當沒有 Claude API Key 時的規則型備援分析"""
    score = 0
    notes = []

    current = data["current_price"]
    rsi    = data.get("rsi") or 50
    macd   = data.get("macd") or 0
    sig    = data.get("macd_signal") or 0
    ma5    = data.get("ma5") or current
    ma20   = data.get("ma20") or current
    ma60   = data.get("ma60") or current
    bb_up  = data.get("bb_upper") or current * 1.05
    bb_lo  = data.get("bb_lower") or current * 0.95
    support    = data.get("support") or current * 0.95
    resistance = data.get("resistance") or current * 1.05
    vol_today  = data.get("vol_today") or 0
    vol_avg5   = data.get("vol_avg5") or 1
    div_yield  = data.get("div_yield") or 0
    pe         = data.get("pe_ratio")

    # RSI
    if rsi < 30:
        score += 3; notes.append(f"RSI={rsi:.1f} 超賣訊號")
    elif rsi < 45:
        score += 1; notes.append(f"RSI={rsi:.1f} 偏低")
    elif rsi > 70:
        score -= 3; notes.append(f"RSI={rsi:.1f} 超買訊號")
    elif rsi > 60:
        score -= 1; notes.append(f"RSI={rsi:.1f} 偏高")

    # MACD
    if macd > sig and macd > 0:
        score += 2; notes.append("MACD 金叉且在零軸上方")
    elif macd > sig:
        score += 1; notes.append("MACD 金叉")
    elif macd < sig and macd < 0:
        score -= 2; notes.append("MACD 死叉且在零軸下方")
    elif macd < sig:
        score -= 1; notes.append("MACD 死叉")

    # 均線多空排列
    if current > ma5 > ma20 > ma60:
        score += 2; notes.append("均線多頭排列")
    elif current < ma5 < ma20 < ma60:
        score -= 2; notes.append("均線空頭排列")
    elif current > ma20:
        score += 1
    else:
        score -= 1

    # 布林通道
    if current < bb_lo:
        score += 2; notes.append("股價跌破布林下軌，超賣反彈機會")
    elif current > bb_up:
        score -= 2; notes.append("股價突破布林上軌，過熱風險")

    # 量能
    if vol_today > vol_avg5 * 1.5 and current > ma5:
        score += 1; notes.append("量增價漲")
    elif vol_today > vol_avg5 * 1.5 and current < ma5:
        score -= 1; notes.append("量增價跌")

    # 基本面（台股殖利率門檻 5%，美股 2.5%）
    div_threshold = 2.5 if market == "us" else 5
    pe_low  = 20 if market == "us" else 15
    pe_high = 35 if market == "us" else 30
    unit = "USD" if market == "us" else "元"

    if div_yield and div_yield >= div_threshold:
        score += 1; notes.append(f"高殖利率 {div_yield:.1f}%")
    if pe and pe < pe_low:
        score += 1; notes.append(f"本益比偏低 {pe:.1f}x")
    elif pe and pe > pe_high:
        score -= 1; notes.append(f"本益比偏高 {pe:.1f}x")

    # 判斷結論
    if score >= 3:
        action = "買進"
        buy_low  = round(max(support * 1.005, current * 0.97), 2)
        buy_high = round(current * 1.02, 2)
        stop_loss = round(support * 0.97, 2)
        summary = f"多項指標偏多（得分 {score}），{notes[0] if notes else ''}，具短線買進機會。"
        tech = (f"RSI={rsi:.1f}{'(超賣)' if rsi<30 else ''}，MACD={'金叉' if macd>sig else '死叉'}，"
                f"股價{'高於' if current>ma20 else '低於'}MA20。布林通道{'下軌支撐' if current<bb_lo else '中軌以上'}，"
                f"成交量{'放大' if vol_today>vol_avg5 else '縮小'}。整體技術面偏多。")
        fund = (f"殖利率 {div_yield or 'N/A'}%，本益比 {pe or 'N/A'}x，ROE {data.get('roe') or 'N/A'}%。"
                f"{'高殖利率提供下檔保護。' if div_yield and div_yield>=div_threshold else ''}"
                f"{'估值合理偏低。' if pe and pe<pe_high else ''}")
        rec = f"建議在 {buy_low}～{buy_high} {unit}分批買進，停損設於 {stop_loss} {unit}。"
        return {"action": action, "summary": summary, "technical_analysis": tech,
                "fundamental_analysis": fund, "recommendation": rec,
                "buy_low": buy_low, "buy_high": buy_high, "stop_loss": stop_loss,
                "sell_low": None, "sell_high": None, "take_profit": None,
                "wait_condition": None,
                "risk_warning": "股市有風險，以上分析僅供參考，請自行評估風險。"}
    elif score <= -3:
        action = "賣出"
        sell_low  = round(current * 0.98, 2)
        sell_high = round(min(resistance * 0.995, current * 1.03), 2)
        take_profit = round(resistance * 0.98, 2)
        summary = f"多項指標偏空（得分 {score}），{notes[0] if notes else ''}，建議減碼或出場。"
        tech = (f"RSI={rsi:.1f}{'(超買)' if rsi>70 else ''}，MACD={'死叉' if macd<sig else '金叉'}，"
                f"股價{'低於' if current<ma20 else '高於'}MA20。整體技術面偏空，下行風險偏高。")
        fund = (f"殖利率 {div_yield or 'N/A'}%，本益比 {pe or 'N/A'}x，ROE {data.get('roe') or 'N/A'}%。"
                f"{'本益比偏高，估值有修正壓力。' if pe and pe>pe_high else '基本面需持續觀察。'}")
        rec = f"建議在 {sell_low}～{sell_high} {unit}逢高賣出，停利目標 {take_profit} {unit}附近。"
        return {"action": action, "summary": summary, "technical_analysis": tech,
                "fundamental_analysis": fund, "recommendation": rec,
                "buy_low": None, "buy_high": None, "stop_loss": None,
                "sell_low": sell_low, "sell_high": sell_high, "take_profit": take_profit,
                "wait_condition": None,
                "risk_warning": "股市有風險，以上分析僅供參考，請自行評估風險。"}
    else:
        action = "觀望"
        summary = f"技術訊號不明確（得分 {score}），建議觀望等待更清晰的方向。"
        tech = (f"RSI={rsi:.1f} 處中性區間，MACD訊號{'偏多' if macd>sig else '偏空'}但力道不足。"
                f"股價於均線附近整理，方向待確認。")
        fund = (f"殖利率 {div_yield or 'N/A'}%，本益比 {pe or 'N/A'}x。基本面尚可，"
                f"但技術面需等待突破訊號。")
        wait = f"等待 RSI 低於 35 或突破壓力位 {resistance:.2f} {unit}後再考慮進場。"
        rec = f"目前不建議新倉，持有者可以 {round(support*0.97,2)} {unit}為停損觀察。"
        return {"action": action, "summary": summary, "technical_analysis": tech,
                "fundamental_analysis": fund, "recommendation": rec,
                "buy_low": None, "buy_high": None, "stop_loss": None,
                "sell_low": None, "sell_high": None, "take_profit": None,
                "wait_condition": wait,
                "risk_warning": "股市有風險，以上分析僅供參考，請自行評估風險。"}


# ─── Flask 路由 ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})
    results = search_stocks(q)
    return jsonify({"results": results})


@app.route("/api/search_us")
def api_search_us():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})
    results = search_us_stocks(q)
    return jsonify({"results": results})


@app.route("/api/analyze")
def api_analyze():
    ticker = request.args.get("ticker", "").strip()
    name   = request.args.get("name", ticker)
    market = request.args.get("market", "tw").lower()

    if not ticker:
        return jsonify({"error": "請提供股票代碼"}), 400

    data = analyze_stock(ticker, market)
    if not data:
        if market == "tw":
            # 台股：嘗試另一個市場後綴
            alt = ticker.replace(".TW", ".TWO") if ticker.endswith(".TW") else ticker.replace(".TWO", ".TW")
            data = analyze_stock(alt, market)
            if not data:
                return jsonify({"error": f"無法取得 {ticker} 的資料，請確認代號是否正確。"}), 404
            ticker = alt
        else:
            return jsonify({"error": f"無法取得 {ticker} 的資料，請確認代號是否正確。"}), 404

    rec = generate_recommendation(ticker, name, data, market)
    data["recommendation"] = rec
    data["name"]   = name
    data["ticker"] = ticker
    data["market_type"] = market

    return jsonify(data)


@app.route("/api/sectors")
def api_sectors():
    market = request.args.get("market", "tw").lower()
    if market == "us":
        return jsonify({"sectors": list(US_SECTORS.keys())})
    cache = get_tw_sector_cache()
    sectors = sorted(cache.keys())
    return jsonify({"sectors": sectors})


@app.route("/api/sector_stocks")
def api_sector_stocks():
    market = request.args.get("market", "tw").lower()
    sector = request.args.get("sector", "").strip()
    if not sector:
        return jsonify({"results": []}), 400

    if market == "us":
        stocks = US_SECTORS.get(sector, [])
        return jsonify({"results": stocks})

    cache = get_tw_sector_cache()
    stocks = cache.get(sector, [])
    return jsonify({"results": stocks})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"股票分析系統啟動於 http://127.0.0.1:{port}")
    app.run(debug=False, port=port)
