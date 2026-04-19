# 股票智能分析系統（台股 / 美股）

輸入股票代碼或公司名稱關鍵字，自動取得技術面、基本面分析，以及 AI 投資建議與買賣操作區間。支援台灣股市（上市、上櫃）與美國股市（NYSE、NASDAQ）雙市場切換。

---

## 功能一覽

| 功能 | 說明 |
|------|------|
| 🔍 智能搜尋 | 台股：輸入代碼（`2330`）或名稱（`台積`）；美股：輸入代碼（`AAPL`）或公司名（`Apple`） |
| 🌐 雙市場切換 | 頁面頂端切換 🇹🇼 台股 / 🇺🇸 美股，自動調整顏色慣例、幣別顯示與分析閾值 |
| 🗣 多語言介面 | 頁面頂端可切換 **繁中 / 日本語 / EN** 三種語言，全介面即時套用 |
| 🗂 產業分類瀏覽 | 搜尋框下方常駐顯示產業 pill 列；點擊任一類別展開該類股清單，一鍵觸發分析 |
| 📊 技術分析 | RSI(14)、MACD(12/26/9)、MA5/MA20/MA60、布林通道、支撐壓力位、量價分析 |
| 💰 基本面分析 | 本益比(P/E)、股價淨值比(P/B)、ROE、殖利率、EPS、營收成長率 |
| 📈 互動圖表 | 價格走勢+均線、布林通道、RSI 圖、MACD 直條圖、成交量圖（可切換） |
| 💵 股利紀錄 | 近 8 次除息日期與股利金額 |
| 🤖 AI 投資建議 | **買進 / 賣出 / 觀望** 三種判斷，附具體操作價格區間、停損/停利點 |

> 顏色慣例：台股 **紅色 = 漲 / 綠色 = 跌**；美股 **綠色 = 漲 / 紅色 = 跌**

---

## 環境需求

- Python **3.9** 以上
- 網路連線（擷取 TWSE/TPEX 報價、Yahoo Finance 及 yfinance 歷史資料）
- （選用）Anthropic API Key，用於啟用 Claude AI 分析

---

## 快速開始

### 方法一：使用啟動腳本（建議）

```bash
# Windows — 雙擊或在 cmd 執行
start.bat

# macOS / Linux
./start.sh
```

腳本會自動：**終止 port 5000 上的舊進程** → 建立虛擬環境 → 安裝相依套件 → 啟動伺服器。

> **注意**：`start.bat` 採純 ASCII 英文撰寫，確保在各種 Windows 語系下皆可正常執行，不會因編碼問題導致指令解析失敗。

### 方法二：手動安裝

```bash
# 1. 建立虛擬環境
python -m venv venv

# 2. 安裝套件（直接使用 venv 內的 python，不需 activate）
venv\Scripts\python.exe -m pip install -r requirements.txt   # Windows
# venv/bin/python -m pip install -r requirements.txt         # macOS / Linux

# 3. 設定 API Key（選用，見下方說明）
copy .env.example .env
# 用文字編輯器開啟 .env，填入 ANTHROPIC_API_KEY

# 4. 啟動伺服器
venv\Scripts\python.exe app.py   # Windows
# venv/bin/python app.py         # macOS / Linux
```

> **為什麼不用 `activate`？** 在部分 Windows 環境下，`call activate.bat` 可能因執行政策或路徑問題失敗，直接使用 `venv\Scripts\python.exe` 更可靠。

### 開啟網頁

```
http://127.0.0.1:5000
```

---

## 設定 Claude AI 分析（選用）

取得 Anthropic API Key 後，在專案根目錄建立 `.env` 檔案：

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxx
```

設定後重啟伺服器，AI 建議將改由 Claude claude-sonnet-4-6 生成，分析內容更完整精準。

**沒有 API Key 也可正常使用**，系統自動啟用規則型備援分析（根據 RSI、MACD、均線排列、布林通道、量能等指標評分判斷）。規則型分析的閾值依市場自動調整：
- 台股：殖利率基準 5%、P/E 合理範圍 15–30
- 美股：殖利率基準 2.5%、P/E 合理範圍 20–35

---

## 專案結構

```
StockAnalysis/
├── app.py                  # Flask 後端（路由、資料擷取、技術指標、AI 分析）
├── requirements.txt        # Python 相依套件清單
├── start.bat               # Windows 一鍵啟動腳本（自動終止舊進程）
├── start.sh                # macOS / Linux 一鍵啟動腳本（自動終止舊進程）
├── .env.example            # 環境變數範本
├── .env                    # 實際環境變數（請勿上傳至版控）
├── templates/
│   └── index.html          # 前端單頁應用（HTML + Chart.js）
└── .claude/
    └── commands/
        └── setup-env.md    # Claude Code 環境建置 Skill（/setup-env）
```

---

## API 路由

| 路由 | 方法 | 參數 | 說明 |
|------|------|------|------|
| `/api/search` | GET | `q` | 台股搜尋（TWSE + TPEX） |
| `/api/search_us` | GET | `q` | 美股搜尋（代理 Yahoo Finance） |
| `/api/analyze` | GET | `ticker`, `name`, `market` (`tw`\|`us`) | 取得並分析指定股票 |
| `/api/sectors` | GET | `market` (`tw`\|`us`) | 取得指定市場的產業分類列表 |
| `/api/sector_stocks` | GET | `market`, `sector` | 取得指定產業的股票清單 |

---

## 資料來源

| 資料 | 來源 |
|------|------|
| 上市股票清單 | [TWSE OpenAPI](https://openapi.twse.com.tw) `STOCK_DAY_ALL` |
| 上櫃股票清單 | [TPEX OpenAPI](https://www.tpex.org.tw/openapi) `tpex_mainboard_quotes` |
| 台股產業分類 | TWSE `t187ap03_L`（上市）、TPEX `mopsfin_t187ap03_O`（上櫃） |
| 美股搜尋 | Yahoo Finance Search API（`/v1/finance/search`，限 US 交易所） |
| 美股產業分類 | 內建 11 個 GICS 產業，各含 ~10 代表性個股 |
| 歷史股價 / 基本面 | [yfinance](https://pypi.org/project/yfinance/)（台股加 `.TW` / `.TWO`；美股直接使用原始代碼） |
| AI 投資建議 | [Anthropic Claude API](https://www.anthropic.com) `claude-sonnet-4-6` |

---

## 使用說明

### 方式一：關鍵字搜尋

- **台股**：輸入代碼（如 `2330`）或名稱關鍵字（如 `台積電`），從下拉清單選取，或直接按 Enter
- **美股**：輸入代碼（如 `AAPL`）或名稱（如 `Apple`），從下拉清單選取

### 方式二：產業分類瀏覽

搜尋框正下方常駐顯示「📊 產業分類」pill 列：

1. 點選任一產業類別（如「半導體」、「科技」）
2. 下方展開該產業的股票清單
3. 點選任一股票卡片 → 直接觸發完整分析
4. 點擊同一 pill 或按 **✕ 收起** 關閉清單

> 台股產業類別從 TWSE/TPEX API 動態載入；美股為 11 個 GICS 產業（科技、金融、醫療保健…）。

### 查看分析結果

4. 系統自動載入約 1 年歷史資料並計算各項指標
5. 查看頁面上方的 **AI 投資建議卡**：
   - 🔴/🟢 **建議買進**：顯示建議買進價格區間（下限～上限）與停損價
   - 🟢/🔴 **建議賣出**：顯示建議賣出價格區間（下限～上限）與停利目標
   - 🟡 **中性觀望**：說明需等待的進場條件
6. 切換「K 線+均線」與「布林通道」圖表標籤查看不同視圖

---

## 常見問題

**Q：雙擊 `start.bat` 出現 `'orlevel' 不是內部或外部命令`？**
A：這是舊版 `start.bat` 含有中文字元、Windows cmd.exe 編碼解析失敗的問題。請確認使用最新版的 `start.bat`（純 ASCII 英文版本）。

**Q：重新執行 `start.bat` 後出現 port 已被占用的錯誤？**
A：最新版 `start.bat` / `start.sh` 會在啟動前自動偵測並終止 port 5000 上的舊進程，不需要手動關閉。若仍失敗，請手動執行 `taskkill //F //IM python.exe`（Windows）。

**Q：產業分類 pill 列沒有顯示？**
A：台股產業資料從 TWSE API 動態載入，需要網路連線。若頁面顯示「無法載入」，確認 TWSE API 可連線後重新整理頁面。

**Q：出現 `Permission denied: venv\Scripts\python.exe`？**
A：通常是 Windows Defender 或防毒軟體即時掃描導致。請稍等幾秒後重試，或將專案資料夾加入防毒軟體例外清單。

**Q：出現 `No module named 'dotenv'`？**
A：代表執行到系統 Python 而非 venv 的 Python。請改用 `venv\Scripts\python.exe app.py` 直接執行，或重新雙擊 `start.bat`。

**Q：搜尋不到上櫃股票？**
A：TPEX API 偶有連線逾時。重新整理頁面後再試，或直接輸入股票代碼按 Enter。

**Q：美股搜尋結果為空？**
A：美股搜尋透過 Yahoo Finance API，偶有連線逾時。請直接輸入正確代碼（如 `AAPL`）按 Enter 進行分析。

---

## 注意事項

- 本系統分析結果**僅供參考**，不構成任何投資建議
- 股市投資有風險，請依個人風險承受能力自行判斷
- yfinance 資料可能有延遲，不適合當沖即時交易參考
- 部分冷門股票可能因 yfinance 資料不足而無法分析

---

## IIS 部署（Windows Server）

若要透過 IIS 對外提供服務，需要額外完成以下設定：

**前置需求**
- 安裝 [HttpPlatformHandler](https://www.iis.net/downloads/microsoft/httpplatformhandler)（在 IIS 官網搜尋下載）
- Python 必須以「**Install for all users**」方式安裝（裝到 `C:\Program Files\Python3xx\`），讓 IIS 服務帳號可以存取

**設定步驟**

1. 修改 `web.config`，將 `processPath` 指向你的 venv python.exe 路徑：
   ```xml
   <httpPlatform processPath="F:\your\path\venv\Scripts\python.exe"
                 arguments="F:\your\path\run_waitress.py" ... />
   ```
2. 建立 `logs\` 資料夾（`web.config` 的 stdout log 路徑需存在）
3. 以**系統管理員**身份解鎖 IIS handlers 設定：
   ```cmd
   %windir%\system32\inetsrv\appcmd.exe unlock config -section:system.webServer/handlers
   ```
4. 重啟 IIS：`iisreset`

---

## 相依套件

```
flask>=3.0.0
yfinance>=0.2.40
pandas>=2.0.0
numpy>=1.24.0
requests>=2.31.0
anthropic>=0.40.0
python-dotenv>=1.0.0
waitress>=3.0.0        # IIS 部署時使用
```
