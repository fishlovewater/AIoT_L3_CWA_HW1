# 部署到 Vercel 教學（台灣天氣預報）

## 先講重點：為什麼是這個架構

**Vercel 無法直接跑 Streamlit。** Streamlit 需要一個長時間執行、與瀏覽器保持
WebSocket 連線的 Python 伺服器；而 Vercel 是「無伺服器（serverless）」平台，只能跑
靜態檔案與短時間的函式，沒有常駐程序。所以原本的 `app.py`（Streamlit）不能放上 Vercel。

因此本專案為 Vercel 另做了一套**不依賴 Streamlit** 的版本，同一份天氣資料邏輯：

```
瀏覽器
  │  載入靜態頁面
  ▼
public/index.html + app.js + styles.css   ← 靜態前端（液態玻璃 UI、Leaflet 地圖、Chart.js 圖表）
  │  fetch("/api/forecast")
  ▼
api/forecast.py  ← Vercel Python 無伺服器函式
  │  直接呼叫 CWA API（無 SQLite，改用函式內短期快取）
  ▼
中央氣象署 F-D0047-091
```

- **沒有資料庫**：Vercel 函式的檔案系統是暫時且唯讀的，無法存 SQLite。改為每次請求
  直接讀 CWA，並用「函式內記憶體快取 30 分鐘」＋「邊緣 CDN 快取」降低請求量。
- **授權碼**：放在 Vercel 專案的環境變數 `CWA_API_KEY`，不會出現在前端或版本庫。

> 原本的 Streamlit 版本（`app.py`、`backend/`、`frontend/`）仍完整保留，可繼續部署到
> **Streamlit Community Cloud**。兩套並存，Vercel 版走 `api/` + `public/`。

---

## 這次為 Vercel 新增的檔案

```
api/
  _cwa.py          # 輕量 CWA 存取＋解析＋每日彙整（只依賴 requests）
  forecast.py      # 無伺服器函式，回傳 JSON 給前端
  requirements.txt # 函式依賴（只有 requests）
public/
  index.html       # 靜態前端
  app.js           # 前端邏輯（呼叫 /api/forecast、畫圖表/表格/地圖/帶傘提醒）
  styles.css       # 液態玻璃樣式
vercel.json        # Vercel 設定（函式資源）
.vercelignore      # 排除 Streamlit 版檔案，避免被誤當成函式
```

### ⚠️ 常見錯誤：`Found app.py but it does not export ... "handler"`

Vercel 的 Python 偵測會把**根目錄的 `.py` 檔**（例如 Streamlit 版的 `app.py`、
`bootstrap.py`、`update_data.py`）當成 serverless 函式，並期待它們匯出 `app`/`handler`，
於是報這個錯。

解法（本專案已處理）：用 `.vercelignore` 把 Streamlit 版的檔案排除，只讓 `api/` 與
`public/` 進到 Vercel。這樣 Vercel 只會把 `api/forecast.py` 當函式，`app.py` 完全不參與部署。
若你日後新增其他根目錄 `.py`，記得一併加進 `.vercelignore`。

---

## 部署步驟

### 1. 把程式碼放上 GitHub
確保 `api/` 與 `public/` 都已提交（`.env`、`data.db` 會被 `.gitignore` 排除，不會上傳）。

```bash
git add api public vercel.json DEPLOY_VERCEL.md
git commit -m "feat: 新增 Vercel 版（靜態前端 + Python 函式）"
git push
```

### 2. 在 Vercel 建立專案
1. 到 https://vercel.com 用 GitHub 登入。
2. **Add New… → Project**，選這個 repo，按 **Import**。
3. Framework Preset 選 **Other**（不需要 build 指令；Vercel 會自動偵測 `public/`
   為靜態輸出、`api/` 為函式）。
4. 先不要按 Deploy，先設定環境變數（下一步）。

### 3. 設定授權碼（重要）
在 **Settings → Environment Variables** 新增：

| Name | Value | Environments |
|------|-------|--------------|
| `CWA_API_KEY` | 你的中央氣象署授權碼 | Production、Preview、Development 全勾 |

> 授權碼只放這裡，不要寫進程式或前端。

### 4. Deploy
按 **Deploy**，等建置完成，會得到一個網址（例如 `https://你的專案.vercel.app`）。
打開就能看到天氣預報頁面。

---

## 本機測試（可選）

安裝 Vercel CLI 後可在本機模擬 Vercel 環境：

```bash
npm i -g vercel
vercel dev        # 第一次會問你連結專案
```

- 本機需要 `CWA_API_KEY`：可用 `vercel env pull` 取回雲端變數，或在本機建 `.env`
  （Vercel CLI 會讀取）。
- 開 `http://localhost:3000` 檢視。

> 若不想裝 CLI，也可先確認函式邏輯：
> `py -3.12 -c "from api._cwa import build_payload; print(len(build_payload()['regions']))"`
> （需先在該終端機設好 `CWA_API_KEY` 環境變數）——本機驗證已證實可回傳 22 個縣市。

---

## 資料如何保持最新（Vercel 版）

- 前端每次載入呼叫 `/api/forecast`。
- 函式優先回傳自己記憶體中 30 分鐘內的快取；過期才重新向 CWA 取。
- 回應也帶 `Cache-Control: s-maxage=1800, stale-while-revalidate=3600`，讓 Vercel
  邊緣節點快取 30 分鐘、並在背景更新。
- **不需要 cron / 排程**：資料是「按需即時抓取」，沒有像 SQLite 那種需要另外更新的問題。

若之後要更省 CWA 請求，可再加 Vercel Cron 定時打 API 暖快取；本版不需要。

---

## 已知限制

- 顯示的是 F-D0047-091「未來一週逐 12 小時」預報，彙整為**每日**高低溫與降雨機率。
- Vercel 免費方案的函式有執行時間與呼叫量上限；一般個人使用足夠。
- 地圖座標使用 CWA 回應提供的縣市經緯度。
- 冷啟動時第一次請求會多花約 1～2 秒安裝/啟動函式，屬正常。
