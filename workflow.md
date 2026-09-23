# 工作流程文件（Workflow）：台灣天氣預報網站

本文件說明**實際完成的專案**是怎麼運作的：資料如何從中央氣象署流到畫面、前後端如何連結、
兩種部署版本的差異。與 [design.md](./design.md)（設計構想）不同，本文件對齊真實程式碼。

技術棧：`CWA API × Python × Requests × Pandas × SQLite × Streamlit`（Streamlit 版）
／`Python WSGI × Requests × 靜態前端（Leaflet + Chart.js）`（Vercel 版）。

---

## 一、整體資料流（共用邏輯）

不論哪個版本，資料處理的核心是同一套：

```
① 中央氣象署 CWA Open Data API
   F-D0047-091（未來一週逐 12 小時）
        │  Requests GET（帶授權碼，timeout + HTTP 錯誤處理）
        ▼
② 解析 JSON（巢狀大寫結構）
   records.Locations[0].Location[] → WeatherElement[]（中文名）
        │  按 (StartTime, EndTime) 時間鍵配對 最高溫/最低溫/降雨機率
        │  缺值 '-' → None（不當 0）；單筆結構異常只略過並計數
        ▼
③ 每個縣市的「逐 12 小時時段」清單
   {geocode, county, lat, lng, startTime, endTime, minT, maxT, pop}
        │  依 geocode + 台灣當地日期彙整
        ▼
④ 每日彙整
   每日最低溫 = MIN(minT)、每日最高溫 = MAX(maxT)、每日降雨機率 = MAX(pop)
        │
        ▼
⑤ 前端呈現
   縣市選單 · 每日高低溫折線圖 · 資料表 · 全台地圖 · 帶傘提醒
```

關鍵原則（對應 [DECISIONS.md](./DECISIONS.md)）：
- **先驗證再實作**：實際打過 API 核對欄位、時間粒度、缺值表示，才定稿解析。
- **保留原始時段**：資料以 12 小時時段為最小單位儲存，唯一鍵含起訖時間，避免同日覆蓋。
- **每日彙整只在查詢時做**：不改變底層粒度，需要時用 SQL `GROUP BY 日期` 取 MIN/MAX。
- **地區用 geocode 識別**：不同縣市不混淆；地圖座標優先用來源提供的經緯度。

---

## 二、兩種版本的架構

### 版本 A：Streamlit 單體（本機 / Streamlit Cloud）

「前後端合一」——同一個 Python 程序既處理資料也畫 UI，靠**函式呼叫**連結。

```
┌──────────────────────────────────────────────┐
│           streamlit_app.py（Streamlit 程序）    │
│                                                │
│  前端(frontend/) ──函式呼叫──▶ 後端(backend/)    │
│   st 元件/玻璃卡片 ◀──DataFrame── SQLite 查詢     │
└───────────────┬────────────────────────────────┘
                │ WebSocket 自動同步
                ▼
            瀏覽器
```

- 資料落地在 SQLite（`data.db`），`update_data.py` 或 app 啟動時（`bootstrap.py`）更新。
- 前端只呼叫 `backend/service.py` 這一層乾淨介面。

### 版本 B：Vercel 靜態前端 + Python 函式

Vercel 無法跑 Streamlit，因此改為「靜態前端 + 無伺服器函式」，靠 **HTTP + JSON** 連結。

```
瀏覽器
  │  所有請求
  ▼
app.py（WSGI 入口，Vercel Python builder）
  ├─ GET /api/forecast → api/_cwa.build_payload() → 回 JSON
  └─ 其他路徑          → 服務 public/ 靜態檔（index.html / app.js / styles.css）
        │  即時呼叫 CWA（無資料庫，30 分鐘行程內快取 + CDN 快取）
        ▼
   中央氣象署 F-D0047-091
```

- 無資料庫：Vercel 檔案系統暫時且唯讀，改為每次請求即時抓取 + 快取。
- `vercel.json` 把所有路徑導向 `app.py`；`pyproject.toml` 指定入口與依賴（只有 requests）。

---

## 三、後端（資料層與邏輯層）

### Streamlit 版 `backend/`

| 檔案 | 職責 |
|------|------|
| `fetcher.py` | 呼叫 CWA API（timeout、HTTP 錯誤）；解析巢狀 JSON；按時間鍵配對；缺值轉 None；`validate()` 拒絕空資料 |
| `database.py` | 建表、參數化查詢、`upsert`（唯一鍵 `(geocode, startTime, endTime)`）；DB 位置可用 `WEATHER_DB_PATH` 設定 |
| `service.py` | **UI 查資料的單一入口**：`list_regions`、`get_region_daily`、`available_days`、`get_day_all_regions`、`umbrella_alert`、`last_updated` |

### Vercel 版 `api/_cwa.py`

同樣的解析與每日彙整邏輯，但**只依賴 `requests`**（不含 pandas/streamlit），
提供 `build_payload()` 一次組出前端要的全部資料（地區清單、每地區每日、座標、可用日期）。

---

## 四、前端（呈現層）

### Streamlit 版 `frontend/`
- `styles.py`：注入 iOS 液態玻璃 CSS，用**帶 key 的 `st.container(key=...)`** 產生穩定樣式 hook
  （不用跨多次 `st.markdown` 的開關 `<div>`）。
- `components.py`：折線圖（matplotlib）、資料表、Folium 地圖（含溫度圖例）、帶傘提醒卡。
- `streamlit_app.py`：組裝上述元件，透過 `backend.service` 取資料，並加 `@st.cache_data`。

### Vercel 版 `public/`
- `index.html`：頁面骨架 + 液態玻璃卡片。
- `app.js`：`fetch("/api/forecast")` → 用 Chart.js 畫折線圖、渲染表格、用 Leaflet 畫地圖、
  判斷帶傘提醒。
- `styles.css`：液態玻璃樣式，響應式。

---

## 五、前後端如何連結

| 版本 | 連結媒介 | 說明 |
|------|----------|------|
| Streamlit | Python 函式呼叫 | `streamlit_app.py` import `backend.service`，傳 DataFrame 給元件畫出來 |
| Vercel | HTTP + JSON | `public/app.js` 打 `/api/forecast`，由 `app.py`（WSGI）回 JSON |

**Streamlit 一次互動流程**：使用者改選單 → Streamlit 重跑 `streamlit_app.py` →
呼叫 `service.get_region_daily()`（命中快取直接回，否則查 SQLite）→ 元件把 DataFrame
畫進玻璃卡片 → WebSocket 推回瀏覽器。

**Vercel 一次載入流程**：瀏覽器載入 `index.html` → `app.js` `fetch('/api/forecast')` →
`app.py` 呼叫 `_cwa.build_payload()`（即時抓 CWA + 30 分鐘快取）→ 回 JSON →
`app.js` 畫圖表/表格/地圖/帶傘提醒。

---

## 六、資料更新機制

| 版本 | 更新方式 |
|------|----------|
| Streamlit（本機）| 手動 `py -3.12 update_data.py`，或 app 啟動時 `bootstrap.ensure_fresh_data()` 自動更新 |
| Streamlit（Cloud）| 靠 app 啟動時自動更新（SQLite 為暫存，重啟自動重抓）|
| Vercel | 無排程；每次請求即時抓 CWA，30 分鐘行程內快取 + CDN `s-maxage` 快取 |

`update_data.py` 特性：可重複執行（唯一鍵 upsert 不重複）、**更新失敗保留上一批可用資料**、
輸出寫入筆數/時間/略過數，**不輸出授權碼**。

---

## 七、開發與驗證順序（實際採用）

1. **先打真實 API 核對結構** → 存樣本 → 寫下 schema 與彙整決策（`DECISIONS.md`）。
2. 實作 `fetcher.py`（解析 + 缺值 + 驗證）、`database.py`（建表 + upsert）。
3. 實作 `service.py`（每日彙整、可用日期、帶傘判斷）。
4. **寫測試並執行**：同日多時段、重複更新、跨縣市同名、缺值、API 失敗（`pytest`）。
5. 實作 Streamlit 前端（`styles.py` / `components.py` / `streamlit_app.py`）。
6. 本機 `streamlit run streamlit_app.py` 驗證選單、圖表、表格、地圖、帶傘提醒、無資料提示。
7. 另做 Vercel 版（`api/_cwa.py` + `app.py` + `public/`），本機模擬驗證各路徑回應。
8. 部署：Streamlit Cloud 或 Vercel（見各自文件）。

---

## 八、測試涵蓋情境

| 情境 | 驗證重點 |
|------|----------|
| 同一天多個 12 小時時段 | 不會因唯一鍵而互相覆蓋；彙整取每日 MIN/MAX |
| 重複執行更新 | upsert 不新增重複列，但會更新預報值與抓取時間 |
| 跨縣市同名 | 用 geocode 區分，不混淆 |
| 缺值 `'-'` | 轉為 None，不當 0；帶傘判斷不誤觸發 |
| API 失敗 | 保留上一批資料，不以空資料覆寫 |
| 帶傘判斷 | 降雨 > 50% 觸發；缺值不觸發 |

---

## 相關文件
- 專案介紹與快速開始：[README.md](./README.md)
- 資料結構驗證與 schema 決策：[DECISIONS.md](./DECISIONS.md)
- Vercel 部署教學與疑難排解：[DEPLOY_VERCEL.md](./DEPLOY_VERCEL.md)
- 設計構想（24 步驟課程地圖）：[design.md](./design.md)
