<div align="center">

# ☀️ 台灣天氣預報 Taiwan Weather Forecast

**用中央氣象署（CWA）開放資料打造的互動式天氣預報網站**

以 `F-D0047-091`（未來一週逐 12 小時預報）為資料源，彙整成每日高低溫與降雨機率，
提供縣市查詢、折線圖、資料表、全台地圖，以及「降雨機率 > 50% 提醒帶傘」。
介面採 **iOS 液態玻璃（Liquid Glass）** 風格。

`CWA API` ·  `Python` · `Streamlit` · `Vercel serverless` · `Leaflet` · `Chart.js`

</div>

---

## 📸 網頁示意

![網頁示意](image.png)

---

## 目錄

- [專案簡介](#專案簡介)
- [功能特色](#功能特色)
- [兩種可執行版本](#兩種可執行版本)
- [資料定義（已用真實-api-核對）](#資料定義已用真實-api-核對)
- [快速開始（本機-streamlit-版）](#快速開始本機-streamlit-版)
- [部署](#部署)
- [專案結構](#專案結構)
- [測試](#測試)
- [環境變數](#環境變數)
- [資料解讀](#資料解讀)
- [已知限制](#已知限制)
- [資料來源與授權](#資料來源與授權)

---

## 專案簡介

這是一個把政府開放資料變成「看得懂、用得上」的天氣網站。核心流程是：

> 向中央氣象署取得開放資料 → 解析巢狀 JSON → 依行政區與當地日期彙整成每日高低溫與降雨機率 → 用互動式前端呈現（選單、折線圖、資料表、地圖）→ 依降雨機率提醒帶傘。

專案刻意做了**兩套前端**，共用同一份資料解析與彙整邏輯，方便部署到不同平台。

---

## 功能特色

| 功能 | 說明 |
|------|------|
| 🏙️ **縣市選單** | 22 個縣市，以 CWA 行政區代碼 `geocode` 識別，同名不混淆 |
| 📈 **每日高低溫折線圖** | 由逐 12 小時時段彙整為每日 `MIN`／`MAX`，一眼看趨勢 |
| 📋 **每日預報資料表** | 每日最低溫、最高溫、降雨機率 |
| 🗺️ **全台溫度地圖** | 各縣市當日最高溫，依溫度分級上色，附圖例；座標取自 CWA 回應 |
| ☔ **帶傘提醒** | 所選地區任一日降雨機率 > 50% 時，首頁顯著提醒 |
| 🕒 **資料版本資訊** | 顯示資料最後更新時間、預報單位；無資料／失敗時顯示友善訊息 |
| 🍏 **液態玻璃 UI** | 半透明毛玻璃卡片、模糊背景、大圓角，響應式支援手機與桌面 |

---

## 兩種可執行版本

本專案提供兩套並存的前端，**共用相同的 CWA 解析與每日彙整邏輯**：

| 版本 | 進入點 | 資料儲存 | 部署平台 | 適用情境 |
|------|--------|----------|----------|----------|
| **Streamlit 版** | `streamlit_app.py` + `backend/` + `frontend/` | SQLite（`data.db`）| Streamlit Community Cloud | 課程展示、本機開發、含歷史累積 |
| **Vercel 版** | `app.py`（WSGI）+ `api/_cwa.py` + `public/` | 無（即時抓取 + 短期快取）| Vercel | 靜態前端 + 無伺服器函式、免資料庫 |

> **為什麼有兩套？** Vercel 是無伺服器平台，**無法執行 Streamlit**（Streamlit 需要常駐、
> 與瀏覽器保持 WebSocket 的伺服器）。要上 Vercel 必須改成「靜態前端 + serverless 函式」，
> 因此另做 Vercel 版；Streamlit 版則保留給 Streamlit Cloud 與本機。

完整的資料流與前後端如何連結，請見 [workflow.md](./workflow.md)。

---

## 資料定義（已用真實 API 核對）

實作前已**實際呼叫 CWA API（HTTP 200）**核對結構，結論記於 [DECISIONS.md](./DECISIONS.md)：

- 資料集 `F-D0047-091` = 「臺灣各縣市**未來一週逐 12 小時**天氣預報」。
- 結構為新版大寫：`records.Locations[0].Location[]`，`Location` 為 **22 縣市**（非鄉鎮）。
- 溫度／降雨欄位為**中文** `ElementName`：`最高溫度`、`最低溫度`、`12小時降雨機率`；
  數值鍵為 `MaxTemperature`／`MinTemperature`／`ProbabilityOfPrecipitation`。
- 來源直接提供 `Latitude`／`Longitude`（地圖優先使用）。
- 缺值以 `"-"` 表示，解析時一律轉為 `None`（不當 0）。
- **保留原始 12 小時時段**（唯一鍵 `(geocode, startTime, endTime)`），畫面再以每日彙整呈現，
  避免同日多時段互相覆蓋。

---

## 快速開始（本機 Streamlit 版）

> Windows 請使用標準 CPython（本專案用 `py -3.12`）。MSYS2/MinGW 版的 Python 無法安裝 wheel。

### 1️⃣ 安裝套件
```powershell
py -3.12 -m pip install -r requirements.txt
```
Linux / macOS：
```bash
python3 -m pip install -r requirements.txt
```

### 2️⃣ 設定授權碼
複製 `.env.example` 為 `.env`，填入你的授權碼（到 https://opendata.cwa.gov.tw 會員專區免費取得）：
```
CWA_API_KEY=你的中央氣象署授權碼
```

### 3️⃣ 抓取資料
```powershell
py -3.12 update_data.py            # 從真實 API 抓取，寫入 data.db
py -3.12 update_data.py --demo     # 無授權碼時用示範資料（畫面會標示為示範）
```

### 4️⃣ 啟動網站
```powershell
py -3.12 -m streamlit run streamlit_app.py
```
Windows 也可直接雙擊 **`run_app.bat`**。瀏覽器開 `http://localhost:8501`。

> App 啟動時會自動確認資料表存在、資料過舊時自動更新（`bootstrap.py`），
> 所以第一次開啟就能看到內容。

---

## 部署

### 🟠 A. Streamlit Community Cloud（Streamlit 版）
1. 程式碼推上 GitHub。
2. 到 https://share.streamlit.io 匯入 repo，主程式選 **`streamlit_app.py`**。
3. App 的 **Settings → Secrets** 設定 `CWA_API_KEY`（雲端不讀 `.env`）。
4. Deploy。
   > 注意：Community Cloud 的 SQLite 為暫存，容器重啟會清空，App 啟動時會自動重抓。

### ▲ B. Vercel（Vercel 版）
完整步驟見 **[DEPLOY_VERCEL.md](./DEPLOY_VERCEL.md)**。摘要：
1. 程式碼推上 GitHub（含 `app.py`、`api/`、`public/`、`vercel.json`、`pyproject.toml`）。
2. Vercel 匯入 repo；**Settings → Environment Variables** 設定 `CWA_API_KEY`。
3. 若遇到 `Found app.py...` 錯誤或 API 404，見 DEPLOY_VERCEL.md 的疑難排解。
4. 確認 **Deployment Protection** 已關閉，否則 `/api/forecast` 會被登入頁擋住。

---

## 專案結構

```
台灣天氣預報/
│
├─ streamlit_app.py        # 【Streamlit 版】主程式（架構 A：單體 + 分層）
├─ bootstrap.py            # 初始化 + 自動更新（app 啟動時呼叫）
├─ update_data.py          # 抓取 CWA → 寫入 SQLite（可重複執行、失敗保留舊資料）
├─ run_app.bat             # Windows 一鍵啟動 Streamlit
│
├─ backend/                # 後端：資料層與邏輯層（不碰 UI）
│   ├─ fetcher.py          #   抓取＋解析（timeout、HTTP 錯誤、時間鍵配對、缺值處理、驗證）
│   ├─ database.py         #   SQLite 建表、參數化查詢、upsert（唯一鍵防重複）
│   └─ service.py          #   UI 查資料的單一入口（每日彙整、可用日期、帶傘判斷）
│
├─ frontend/               # 前端：呈現層（Streamlit）
│   ├─ styles.py           #   液態玻璃 CSS（用 st.container(key=) 穩定容器）
│   └─ components.py       #   折線圖、表格、地圖（含圖例）、帶傘提醒
│
├─ data/geo.py             # geocode → 座標 備援對照表（來源無座標時使用）
│
├─ app.py                  # 【Vercel 版】Python WSGI 入口：/api/forecast + 靜態前端
├─ api/_cwa.py             #   輕量 CWA 存取＋解析＋每日彙整（只依賴 requests）
├─ public/                 #   【Vercel 版】靜態前端
│   ├─ index.html          #     頁面骨架
│   ├─ app.js              #     前端邏輯（fetch /api/forecast、畫圖表/表格/地圖/帶傘提醒）
│   └─ styles.css          #     液態玻璃樣式
├─ vercel.json             #   Vercel 路由設定（全部導向 app.py）
├─ pyproject.toml          #   Vercel Python 入口與依賴
│
├─ tests/                  # pytest 測試 + 示範資料 fixture
│   ├─ test_fetcher.py
│   ├─ test_database_service.py
│   ├─ test_update_data.py
│   └─ fixtures/           #   示範資料、真實 API 樣本
│
├─ requirements.txt        # Streamlit 版依賴
├─ .env.example            # 環境變數範本（不含真實金鑰）
├─ DECISIONS.md            # 資料結構驗證與 schema 決策
├─ DEPLOY_VERCEL.md        # Vercel 部署教學與疑難排解
├─ design.md / workflow.md # 設計文件與工作流程
└─ README.md               # 本文件
```

---

## 測試
```powershell
py -3.12 -m pytest -q
```
測試涵蓋：**同日多時段不覆蓋**、**重複更新不重複**、**跨縣市同名區分**、**缺值處理**、
**API 失敗保留舊資料**、**帶傘判斷（含缺值不誤觸發）**。

---

## 環境變數

| 變數 | 說明 | 預設 |
|------|------|------|
| `CWA_API_KEY` | 中央氣象署授權碼（**必填**）| 無 |
| `WEATHER_DB_PATH` | SQLite 檔案位置（Streamlit 版，可選）| 專案內 `data.db` |

> - 本機：放在 `.env`（已被 `.gitignore` 排除）。
> - Streamlit Cloud：放在 App 的 Secrets。
> - Vercel：放在專案的 Environment Variables。
> - 授權碼**不會**出現在原始碼、前端或版本庫中。

---

## 資料解讀

- **每日最高／最低溫**：由當日多個 12 小時時段取 `MAX`／`MIN` 彙整而得。
- **降雨機率**：取當日各時段的**最大值**（較保守，利於帶傘提醒）。
- **地圖顏色**：代表各縣市「當日最高溫」，分級：
  🔵 `< 20°C`　🟢 `20–25°C`　🟠 `25–30°C`　🔴 `> 30°C`　⚪ 無資料。
- **帶傘提醒**：所選地區任一日降雨機率 > 50% 即提醒。

---

## 已知限制

- 僅使用 `F-D0047-091`（一週逐 12 小時，彙整為每日）；未含即時觀測、空氣品質、地震等。
- Streamlit 版的 SQLite 在雲端為暫存；Vercel 版無資料庫、每次即時抓取 + 短期快取。
- 地區為**縣市層級**（此資料集 `Location` 即縣市，無鄉鎮細分）。
- 完整無障礙（WCAG）合規仍需以輔助科技實測與專家審查驗證。

---

## 資料來源與授權

- 資料來源：**交通部中央氣象署**開放資料平台 — https://opendata.cwa.gov.tw
- 資料採「政府資料開放授權條款」，使用時請標示來源。
- 本專案僅供學習與展示用途，實際數據以官方公告為準。

<div align="center">

Made for learning · Powered by CWA Open Data

</div>
