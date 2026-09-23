# 開發工作流程文件（Workflow）：台灣天氣預報網站

本文件依據 [design.md](./design.md) 撰寫，說明這個專案「有哪些功能、每個功能怎麼做」，並特別著重在**前端、後端，以及前後端如何連結**。

技術棧：`CWA API × Python × Requests × Pandas × SQLite × Streamlit（+ Folium）`，介面採 iOS 液態玻璃風格。

> 本文件與 [design.md](./design.md) 的「重要設計決策」一致，重點：
> 1. 先存一份真實 API 回應再定稿 `parse()`（不憑欄位名推定結構）。
> 2. **保留原始預報時段**，唯一鍵 `(geocode, startTime, endTime)`，需要每日視圖時另用 SQL 彙整。
> 3. 地區用**縣市+鄉鎮+行政區代碼（geocode）**識別，避免同名混淆。
> 4. **更新程式內建於 app**，與網站共用同一份資料、同一環境（解決本機排程與雲端資料庫接不起來的問題）。
> 5. 缺值以 `None` 表示、不當 0；畫面顯示「最後更新時間 / 目前預報時段 / 無資料提示」。

---

## 一、架構定位：這個專案的「前端」與「後端」是什麼？

這個專案用 Streamlit 開發。**Streamlit 的特性是「前後端合一」**：同一支 Python 程式，既負責運算與資料存取（後端職責），也負責畫出網頁介面（前端職責）。它啟動一個 Web 伺服器，把 Python 產生的元件透過 WebSocket 即時推送到瀏覽器渲染。

因此本專案有兩種可行的架構，本文件兩種都說明：

- **架構 A（本專案主要採用）**：Streamlit 單體式。用「邏輯分層」把後端（資料層 / 邏輯層）與前端（呈現層）在程式碼中切開，透過**函式呼叫**連結。
- **架構 B（進階選項）**：真正的前後端分離。後端用 FastAPI 提供 REST API，前端另做（或仍用 Streamlit 當 client），透過 **HTTP + JSON** 連結。

```
架構 A（單體，建議入門）
┌──────────────────────────────────────────────┐
│                app.py (Streamlit 進程)           │
│                                                │
│  ┌─────────────┐  函式呼叫   ┌──────────────┐   │
│  │ 前端 (UI 層) │ ─────────▶ │ 後端 (資料/邏輯)│  │
│  │ st 元件      │ ◀───────── │ SQLite 查詢     │  │
│  │ 玻璃卡片      │  回傳 DF   │ Pandas 處理     │  │
│  └─────────────┘            └──────────────┘   │
└──────────────────────────────────────────────┘
        │ WebSocket 自動同步
        ▼
    瀏覽器（使用者）

架構 B（前後端分離，進階）
┌───────────┐  HTTP GET /api/... ┌────────────────┐
│ 前端        │ ─────────────────▶ │ 後端 FastAPI    │
│ (Streamlit/ │ ◀───────────────── │ 查 SQLite、回 JSON│
│  React)     │      JSON          └────────────────┘
└───────────┘
```

---

## 二、專案檔案結構

```
taiwan-weather/
├── app.py                  # 前端主程式（Streamlit 入口、UI 組裝）
├── backend/
│   ├── __init__.py
│   ├── fetcher.py          # 後端：呼叫 CWA API、解析 JSON
│   ├── database.py         # 後端：SQLite 建表、寫入、查詢
│   └── service.py          # 後端：對前端暴露的資料服務函式
├── frontend/
│   ├── styles.py           # 前端：iOS 液態玻璃 CSS 注入
│   └── components.py       # 前端：玻璃卡片、圖表、地圖等 UI 元件
├── data/
│   └── geo.py              # geocode → 經緯度對照表（給地圖用）
├── bootstrap.py            # 初始化 + 自動更新（app 啟動時呼叫）
├── update_data.py          # 抓資料寫入 DB（app 內部呼叫，或本機手動/排程）
├── sample_response.json    # 真實 API 回應樣本（不進版控，供核對結構）
├── data.db                 # SQLite 資料庫（不進版控，雲端為暫存）
├── requirements.txt
├── .env                    # 本機 API Key（不進版控）
├── .streamlit/
│   ├── config.toml         # Streamlit 設定（可選）
│   └── secrets.toml        # 本機測試 st.secrets（不進版控）
└── .gitignore
```

> **Community Cloud 不讀 `.env`**：雲端的機密改用 `st.secrets`（在 Cloud 後台的 Secrets 設定，或本機的 `.streamlit/secrets.toml`）。程式用一支 `_get_api_key()` 同時相容本機與雲端（見下方 `fetcher.py`）。`.streamlit/secrets.toml` 與 `.env` 都不可進版控。

分層原則（呼應 design.md「程式結構清晰」）：
- **後端（backend/）**：只負責「拿資料、處理資料、存取資料庫」，不碰任何 UI。
- **前端（frontend/ + app.py）**：只負責「排版、樣式、把資料畫出來」，不直接寫 SQL。
- 兩者透過 `backend/service.py` 這一層乾淨的函式介面連結。

---

## 三、後端（Backend）：資料層與邏輯層

後端負責 design.md 的步驟 3–10、20。分三個模組。

### 3.1 `fetcher.py` — 從 CWA 取得並解析資料（步驟 4、5、6）

職責：呼叫 CWA API → 解析巢狀 JSON → 提取 MinT / MaxT → 回傳乾淨的 list。

> **動工前必做**：先執行一次 `fetch_raw()` 並把回應存成 `sample_response.json`，用它核對真實欄位路徑、`weatherElement` 的 `elementName`、時間欄位（`startTime`/`endTime`）與有無 `geocode`。下方程式以常見結構示意，實際路徑以樣本為準（見 design.md 步驟 4.5）。

```python
# backend/fetcher.py
import os, json, requests

BASE = 'https://opendata.cwa.gov.tw/api/v1/rest/datastore'
DATASET = 'F-D0047-091'   # 鄉鎮天氣預報（一週）

def _get_api_key():
    """取得 CWA 授權碼：優先讀 st.secrets（Community Cloud），
    退回讀環境變數（本機 .env）。兩種環境共用同一份程式。"""
    try:
        import streamlit as st
        if 'CWA_API_KEY' in st.secrets:
            return st.secrets['CWA_API_KEY']
    except Exception:
        pass
    return os.environ['CWA_API_KEY']

def fetch_raw():
    """呼叫 CWA API，回傳原始 JSON。"""
    url = f'{BASE}/{DATASET}'
    headers = {'Authorization': _get_api_key()}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()

def save_sample(data, path='sample_response.json'):
    """保存一份真實回應，供核對結構（動工前先跑一次）。"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse(data):
    """按時間鍵配對 MinT/MaxT/PoP，保留原始時段，缺值以 None 表示。
    回傳 list[dict]。實際欄位路徑與 PoP 的 elementName 請先用 sample_response.json 核對。"""
    records = []
    top = data['records']['locations'][0]
    county = top.get('locationsName')          # 縣市層（視實際結構）
    for loc in top['location']:
        town = loc['locationName']
        geocode = loc.get('geocode')
        elem = {e['elementName']: e for e in loc['weatherElement']}
        mint = _index_by_time(elem.get('MinT'))
        maxt = _index_by_time(elem.get('MaxT'))
        # 降雨機率：一週預報常見為 'PoP12h'（12 小時降雨機率）；
        # 若樣本顯示是 'PoP' 或 'PoP6h'，把下行的鍵改成實際名稱。
        pop = _index_by_time(elem.get('PoP12h') or elem.get('PoP'))
        # 時間鍵取三者聯集，任何一項缺值都以 None 保留（不當 0）
        for key in sorted(set(mint) | set(maxt) | set(pop)):
            start, end = key
            records.append({
                'geocode': geocode, 'county': county, 'town': town,
                'startTime': start, 'endTime': end,
                'minT': _to_int(mint.get(key)),      # 缺值 → None
                'maxT': _to_int(maxt.get(key)),
                'pop':  _to_int(pop.get(key)),       # 降雨機率(%)，缺值 → None
            })
    return records

def _index_by_time(element):
    """weatherElement → {(startTime, endTime): value}。"""
    out = {}
    if not element:
        return out
    for t in element['time']:
        key = (t.get('startTime'), t.get('endTime') or t.get('startTime'))
        out[key] = t['elementValue'][0]['value'] if t.get('elementValue') else None
    return out

def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
```

### 3.2 `database.py` — SQLite 存取（步驟 8、9、10）

職責：建表、寫入（去重）、查詢。這是後端與資料的邊界。

```python
# backend/database.py
import sqlite3, pandas as pd

DB_PATH = 'data.db'

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS TemperatureForecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                geocode   TEXT,
                county    TEXT,
                town      TEXT,
                startTime TEXT,
                endTime   TEXT,
                minT REAL,           -- 可為 NULL（缺值）
                maxT REAL,
                pop  REAL,           -- 降雨機率(%)，可為 NULL（缺值）
                fetchedAt TEXT,      -- 抓取時間，供顯示「最後更新時間」
                UNIQUE(geocode, startTime, endTime)   -- 保留原始時段、避免覆蓋
            )
        """)

def save(records, fetched_at):
    """upsert：同 (geocode,起,訖) 更新而非重複新增。不可用 to_sql(replace)。"""
    with get_conn() as conn:
        conn.executemany("""
            INSERT INTO TemperatureForecasts
                (geocode, county, town, startTime, endTime, minT, maxT, pop, fetchedAt)
            VALUES (:geocode,:county,:town,:startTime,:endTime,:minT,:maxT,:pop,:fetchedAt)
            ON CONFLICT(geocode, startTime, endTime) DO UPDATE SET
                minT=excluded.minT, maxT=excluded.maxT, pop=excluded.pop,
                fetchedAt=excluded.fetchedAt
        """, [{**r, 'fetchedAt': fetched_at} for r in records])
        conn.commit()

def last_fetched_at():
    """回傳資料庫最新抓取時間；空表回傳 None（供判斷是否需更新）。"""
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(fetchedAt) FROM TemperatureForecasts").fetchone()
    return row[0] if row else None

def query_df(sql, params=()):
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)
```

### 3.3 `service.py` — 對前端暴露的資料服務（前後端的連結點）

這一層是**前端唯一會呼叫的後端入口**。前端不直接寫 SQL、不直接碰 requests，只呼叫這裡的函式。這就是架構 A 中「前後端連結」的關鍵介面。

```python
# backend/service.py
from . import database as db

def list_regions():
    """給下拉選單用：回傳 [{'label':'臺北市 中正區','geocode':'6300500'}, ...]。
    用縣市+鄉鎮顯示、geocode 識別，避免同名鄉鎮混淆。"""
    df = db.query_df(
        "SELECT DISTINCT county, town, geocode FROM TemperatureForecasts "
        "ORDER BY county, town")
    return [{'label': f"{r.county} {r.town}", 'geocode': r.geocode}
            for r in df.itertuples()]

def get_region_week(geocode):
    """給折線圖/表格/帶傘提醒用：某地區的原始時段序列（含降雨機率 pop）。"""
    return db.query_df(
        "SELECT startTime, endTime, minT, maxT, pop FROM TemperatureForecasts "
        "WHERE geocode = ? ORDER BY startTime", (geocode,))

def available_days():
    """給日期選擇器用：資料庫實際有的日期清單（避免選到沒資料的日期）。"""
    df = db.query_df(
        "SELECT DISTINCT substr(startTime,1,10) AS day FROM TemperatureForecasts "
        "ORDER BY day")
    return df['day'].tolist()

def get_day_all_regions(day):
    """給地圖用：某一天所有地區的每日高低溫彙整。"""
    return db.query_df(
        "SELECT geocode, county, town, "
        "       MIN(minT) AS minT, MAX(maxT) AS maxT "
        "FROM TemperatureForecasts WHERE substr(startTime,1,10) = ? "
        "GROUP BY geocode, county, town", (str(day),))

def last_updated():
    """給畫面顯示『最後更新時間』。"""
    return db.last_fetched_at()
```

### 3.4 資料更新流程 `update_data.py`（步驟 7、20）

把「抓 → 解析 → 存」串起來，可手動執行或排程。

```python
# update_data.py
from datetime import datetime
from backend import fetcher, database

def _load_local_env():
    """本機才需要載入 .env；雲端用 st.secrets，沒有 dotenv 也不會壞。"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

def run():
    _load_local_env()                      # 本機讀 .env；雲端無此檔也 OK
    database.init_db()
    raw = fetcher.fetch_raw()              # 步驟 4
    fetcher.save_sample(raw)               # 保存真實回應供核對（首次特別重要）
    records = fetcher.parse(raw)           # 步驟 5、6
    database.save(records, datetime.now().isoformat(timespec='seconds'))  # 步驟 8、9
    print(f"已更新 {len(records)} 筆資料")

if __name__ == '__main__':
    run()
```

**更新機制與部署一致（決策 4）**：更新程式要跑在「網站讀資料的同一環境」。因此建議由 app 內建更新（見第 5.3 節 `ensure_fresh_data`），而非靠外部本機排程去寫一份雲端拿不到的 `data.db`。本機開發時也可用工作排程器/cron 呼叫 `python update_data.py`，但那只更新本機檔案。

---

## 四、前端（Frontend）：呈現層與 iOS 液態玻璃介面

前端負責 design.md 的步驟 11–19，以及附錄 A 的玻璃樣式。

### 4.1 `styles.py` — 注入液態玻璃 CSS（附錄 A）

```python
# frontend/styles.py
import streamlit as st

def inject_glass_css():
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg,#a1c4fd 0%,#c2e9fb 50%,#d4fc79 100%);
        background-attachment: fixed;
    }
    .glass-card {
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid rgba(255,255,255,0.35);
        border-radius: 24px;
        box-shadow: 0 8px 32px rgba(31,38,135,0.2);
        padding: 20px 24px; margin-bottom: 18px;
    }
    .glass-header {
        background: rgba(255,255,255,0.25);
        backdrop-filter: blur(30px);
        border-radius: 28px; border: 1px solid rgba(255,255,255,0.4);
        padding: 24px; text-align: center;
    }
    div[data-baseweb="select"] > div, .stDataFrame {
        background: rgba(255,255,255,0.18) !important;
        backdrop-filter: blur(12px);
        border-radius: 16px !important;
        border: 1px solid rgba(255,255,255,0.3);
    }
    /* 帶 key 的 container 才能真正把元件包進玻璃卡片 */
    .st-key-region_card, .st-key-chart_card,
    .st-key-table_card, .st-key-map_card {
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid rgba(255,255,255,0.35);
        border-radius: 24px;
        box-shadow: 0 8px 32px rgba(31,38,135,0.2);
        padding: 20px 24px; margin-bottom: 18px;
    }
    /* 帶傘提醒的玻璃警示卡（偏暖色調，深色文字確保對比） */
    .glass-warn {
        background: rgba(255, 214, 102, 0.30);
        backdrop-filter: blur(16px) saturate(160%);
        -webkit-backdrop-filter: blur(16px) saturate(160%);
        border: 1px solid rgba(255,255,255,0.45);
        border-radius: 20px;
        box-shadow: 0 6px 24px rgba(180,120,20,0.25);
        padding: 14px 20px; margin-bottom: 16px;
        color: #4a3200; font-size: 1.05rem;
    }
    </style>
    """, unsafe_allow_html=True)
```

> `st.container(key="chart_card")` 會產生 class `st-key-chart_card`。若你的 Streamlit 版本命名不同，用瀏覽器開發者工具確認實際 class 再調整選擇器。

### 4.2 `components.py` — 可重用 UI 元件

> **玻璃卡片不要用 `glass_open()/glass_close()`**：兩次 `st.markdown` 輸出開/關 `<div>` 無法可靠包住中間的 Streamlit 元件。改用**帶 `key` 的 `st.container()`**，再用 CSS 對 `.st-key-<key>` 套樣式（見第四節 4.1 與附錄 A.2）。

```python
# frontend/components.py
import streamlit as st
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
from data.geo import GEO_COORDS   # {geocode: (lat, lng)}

def temperature_chart(df):
    """折線圖（步驟 14）：X 軸用時段起始時間，缺值自動斷線。"""
    if df.empty:
        st.info('此地區目前沒有預報資料。')
        return
    fig, ax = plt.subplots()
    ax.plot(df['startTime'], df['maxT'], marker='o', label='MaxT')
    ax.plot(df['startTime'], df['minT'], marker='o', label='MinT')
    ax.legend(); ax.set_xlabel('時段'); ax.set_ylabel('°C')
    fig.autofmt_xdate()
    st.pyplot(fig)

def data_table(df):
    """資料表（步驟 15）：一併顯示降雨機率。"""
    if df.empty:
        st.info('沒有可顯示的資料。')
        return
    st.dataframe(df[['startTime', 'endTime', 'minT', 'maxT', 'pop']],
                 use_container_width=True)


def umbrella_reminder(week_df, day=None, threshold=50):
    """帶傘提醒（新功能）：若所選地區有時段降雨機率 > threshold(%)，
    在首頁以液態玻璃警示卡提醒使用者帶傘。
    - day 有值時只看當天的時段；否則看整週。
    - pop 為 None（缺值）不觸發、也不誤判為 0。"""
    if week_df is None or week_df.empty or 'pop' not in week_df:
        return

    df = week_df.copy()
    if day:  # 只看所選日期的時段
        df = df[df['startTime'].str.startswith(str(day))]

    valid = df[df['pop'].notna()]
    if valid.empty:
        return

    over = valid[valid['pop'] > threshold]
    if over.empty:
        return

    max_pop = int(over['pop'].max())
    # 列出達標的時段，讓使用者知道是哪幾段會下雨
    slots = "、".join(over['startTime'].tolist()[:3])
    scope = f"{day} " if day else "本週 "
    st.markdown(
        f'<div class="glass-warn">☔ <b>記得帶傘！</b>'
        f'{scope}最高降雨機率 <b>{max_pop}%</b>（門檻 {threshold}%）。'
        f'可能降雨時段：{slots}</div>',
        unsafe_allow_html=True,
    )


def pop_note(week_df):
    """在折線圖下方顯示各時段降雨機率的小提示（可選）。"""
    if week_df is None or week_df.empty or week_df['pop'].isna().all():
        return
    avg = week_df['pop'].dropna().mean()
    st.caption(f"平均降雨機率：{avg:.0f}%")

def taiwan_map(day_df):
    """Folium 地圖（步驟 17、18）：用 geocode 對座標，依平均溫度上色。"""
    if day_df.empty:
        st.info('所選日期沒有預報資料。')
        return
    m = folium.Map(location=[23.7, 121], zoom_start=7)
    for row in day_df.itertuples():
        coord = GEO_COORDS.get(row.geocode)
        if not coord or row.minT is None or row.maxT is None:
            continue                       # 缺座標或缺值就略過
        avg = (row.minT + row.maxT) / 2
        folium.CircleMarker(
            location=coord, radius=10, fill=True,
            color=_color_by_temp(avg),
            popup=f"{row.county} {row.town}: {avg:.0f}°C"
        ).add_to(m)
    st_folium(m, width=700)

def _color_by_temp(t):
    if t < 20: return 'blue'
    if t < 25: return 'green'
    if t < 30: return 'orange'
    return 'red'
```

### 4.3 前端各功能對應

| 功能 | 步驟 | 前端元件 | 呼叫的後端服務 |
|------|------|----------|----------------|
| 下拉選單選地區 | 13 | `st.selectbox`（label 顯示、geocode 識別）| `service.list_regions()` |
| 一週高低溫折線圖 | 14 | `temperature_chart()` | `service.get_region_week(geocode)` |
| 資料表格 | 15 | `data_table()` | `service.get_region_week(geocode)` |
| 日期選擇 | 18 | `st.selectbox`（選項來自 DB）| `service.available_days()` |
| 台灣地圖 | 17、18 | `taiwan_map()` | `service.get_day_all_regions(day)` |
| 最後更新時間 | 16 | `st.caption` | `service.last_updated()` |
| **帶傘提醒（降雨>50%）** | 新增 | `umbrella_reminder()` | `service.get_region_week(geocode)` |

### 4.4 帶傘提醒功能（新增）

**功能**：使用者選定地區後，若該地區（可再限定所選日期）**任一預報時段的降雨機率 > 50%**，就在首頁最上方以液態玻璃警示卡提醒「記得帶傘」，並顯示最高降雨機率與可能降雨的時段。

**需要的資料**：各時段的降雨機率 `pop`（%）。
- **從哪取得**：CWA 一週預報資料集中的降雨機率欄位（常見 `elementName` 為 `PoP12h`，即 12 小時降雨機率；實際名稱請以 `sample_response.json` 為準）。
- **資料流**：`fetcher.parse()` 一併擷取 `pop` → 存入 `TemperatureForecasts.pop` → `service.get_region_week()` 一併回傳 → 前端 `umbrella_reminder()` 判斷是否超過門檻。

**製作重點**：
- 門檻預設 50%，做成 `threshold` 參數方便調整。
- `pop` 為缺值（`None`）時**不觸發、也不當 0**，避免誤判。
- 提醒卡用暖色調玻璃樣式（`.glass-warn`），與一般資訊卡區隔；深色文字確保對比度（WCAG AA）。
- 放在 `app.py` 地區/日期選擇之後、圖表之前，讓提醒出現在首頁明顯位置。

---

## 五、前後端如何連結（重點）

### 5.1 架構 A：函式呼叫連結（本專案主線）

`app.py` 是前端入口。它 **import 後端 service**，用函式呼叫取得資料，再交給前端元件畫出來。連結媒介是「Python 函式的參數與回傳值（DataFrame）」，不需要 HTTP。

```python
# app.py — 前端組裝，透過 service 連結後端
import streamlit as st
from backend import service                 # ← 連結後端的唯一入口
from bootstrap import ensure_fresh_data     # 初始化 + 自動更新（見 5.3）
from frontend.styles import inject_glass_css
from frontend import components as ui

# 本機載入 .env；Community Cloud 用 st.secrets，沒有 dotenv 也不會壞
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(page_title="Taiwan Weather Forecast", layout="wide")
inject_glass_css()                          # 套用玻璃樣式

ensure_fresh_data()                         # 確保資料表存在且不過舊（決策 4）

# 標題玻璃橫幅（純展示 HTML，可用 markdown）＋ 最後更新時間
st.markdown('<div class="glass-header"><h1>Taiwan Weather Forecast</h1></div>',
            unsafe_allow_html=True)
updated = service.last_updated()
st.caption(f"資料最後更新時間：{updated or '尚無資料'}")

regions = service.list_regions()            # 後端 → 前端
if not regions:                             # 空資料明確提示
    st.warning('目前沒有預報資料，請稍後再試或手動執行 update_data.py。')
    st.stop()

# --- 控制列：地區 + 日期（帶 key 的 container 才包得住玻璃卡片）---
with st.container(key="region_card"):
    col1, col2 = st.columns(2)
    with col1:
        labels = [r['label'] for r in regions]
        idx = st.selectbox('選擇地區', range(len(labels)),
                           format_func=lambda i: labels[i])
        geocode = regions[idx]['geocode']
    with col2:
        days = service.available_days()     # 日期選項來自 DB，非預設今天
        day = st.selectbox('選擇日期', days) if days else None

# --- 帶傘提醒：任一時段降雨機率 > 50% 就在首頁提醒（新功能）---
week_df = cached_week(geocode)              # 後端 → 前端（含快取，含 pop 欄位）
ui.umbrella_reminder(week_df, day, threshold=50)

# --- 折線圖 ---
with st.container(key="chart_card"):
    if not week_df.empty:
        st.subheader(f"{labels[idx]} 一週高低溫")
        st.caption(f"預報時段：{week_df['startTime'].min()} ~ {week_df['endTime'].max()}")
    ui.temperature_chart(week_df)
    ui.pop_note(week_df)                    # 各時段降雨機率小提示

# --- 資料表 ---
with st.container(key="table_card"):
    ui.data_table(week_df)

# --- 地圖 ---
with st.container(key="map_card"):
    if day:
        st.subheader(f"{day} 全台溫度地圖")
        ui.taiwan_map(cached_day(day))      # 後端 → 前端（含快取）
    else:
        st.info('沒有可用日期。')
```

快取包一層（放在 `app.py` 或 `frontend`）：
```python
@st.cache_data(ttl=1800)   # 對齊資料更新頻率（見下方說明）
def cached_week(geocode):
    return service.get_region_week(geocode)

@st.cache_data(ttl=1800)
def cached_day(day):
    return service.get_day_all_regions(day)
```

**連結流程（一次使用者互動）**：
1. 使用者在瀏覽器改變下拉選單 →
2. Streamlit 透過 WebSocket 通知伺服器，**從頭重跑 `app.py`** →
3. `app.py` 呼叫 `cached_week(geocode)`（前端 → 後端；命中快取則直接回、未命中才查 DB）→
4. `service` 呼叫 `database.query_df` 查 SQLite，回傳 DataFrame（後端 → 前端）→
5. 前端元件把 DataFrame 畫進帶 key 的玻璃容器 →
6. Streamlit 把新畫面推回瀏覽器。

> **快取注意（重要）**：`@st.cache_data(ttl=...)` 在期限內會**持續回傳舊結果**，即使背景已更新資料。因此 `ttl` 要**對齊資料更新頻率**（CWA 一週預報約每 6 小時更新，這裡設 30 分鐘～數小時皆合理），不要設太長以免顯示過期預報。資料更新後若要立即反映，可呼叫 `st.cache_data.clear()`。畫面已顯示「最後更新時間」，讓使用者能判斷新舊。

### 5.2 架構 B：HTTP + JSON 連結（進階，真正前後端分離）

若要做成標準 client-server，把後端獨立成 FastAPI 服務，前端改用 HTTP 呼叫。

**後端（FastAPI）**：
```python
# api_server.py
from fastapi import FastAPI
from backend import service

app = FastAPI()

@app.get("/api/regions")
def regions():
    return service.list_regions()

@app.get("/api/forecast")
def forecast(region: str):
    return service.get_region_week(region).to_dict(orient='records')

@app.get("/api/map")
def map_data(date: str):
    return service.get_day_all_regions(date).to_dict(orient='records')
```
啟動：`uvicorn api_server:app --reload --port 8000`

**前端（改用 HTTP 取資料）**：
```python
import requests, pandas as pd
API = "http://localhost:8000"

regions = requests.get(f"{API}/api/regions").json()
region = st.selectbox('選擇地區', regions)
week_df = pd.DataFrame(requests.get(
    f"{API}/api/forecast", params={"region": region}).json())
```

此時連結媒介變成 **HTTP 請求 + JSON 回應**，前後端可各自部署、各自擴充（甚至前端換成 React 也不影響後端）。

**兩種架構比較**

| 面向 | 架構 A（Streamlit 單體） | 架構 B（FastAPI + 前端） |
|------|--------------------------|--------------------------|
| 連結方式 | Python 函式呼叫 | HTTP + JSON |
| 開發難度 | 低，適合入門與課程 | 較高 |
| 部署 | 一個服務 | 前後端各一個服務 |
| 擴充性 | 適合資料儀表板 | 適合多前端、對外開放 API |
| 建議 | **本專案採用** | 有需要對外提供 API 時再升級 |

### 5.3 初始化與自動更新（`bootstrap.py`，決策 4）

第一次執行 `app.py` 時資料表可能還沒建立、也還沒有資料；部署到雲端時本機排程也碰不到雲端資料庫。解法是把「初始化 + 自動更新」內建到 app，由 `app.py` 在最前面呼叫一次，讓更新與網站在同一環境、共用同一份資料。

```python
# bootstrap.py
from datetime import datetime, timedelta
from backend import database
import update_data

def ensure_fresh_data(max_age_hours=6):
    """建表 → 若無資料或資料過舊，自行抓一次。app 啟動時呼叫。"""
    database.init_db()                        # 表不存在就建立
    last = database.last_fetched_at()         # 取最新抓取時間
    if last is None or _older_than(last, max_age_hours):
        try:
            update_data.run()                 # 抓 API → 寫入同一份 DB
        except Exception as e:
            import streamlit as st
            st.warning(f'自動更新資料失敗，將沿用現有資料：{e}')

def _older_than(iso_str, hours):
    try:
        return datetime.fromisoformat(iso_str) < datetime.now() - timedelta(hours=hours)
    except (TypeError, ValueError):
        return True
```

要點：
- 用 `@st.cache_resource` 或 session flag 可避免每次互動都檢查更新（只在首次載入檢查一次）。
- API 失敗時不讓網站掛掉：沿用現有資料並顯示提示（呼應「無資料 / API 失敗提示」）。

---

## 五之二、部署到 Streamlit Community Cloud（本專案採用）

本專案部署在 **Streamlit Community Cloud**。這對前面的設計有幾個具體影響，務必照做：

### 1. 機密改用 `st.secrets`，不是 `.env`

Community Cloud **不會讀取 `.env`**。API Key 要放在 Cloud 的 Secrets 設定（App 頁面 → Settings → Secrets），格式為 TOML：

```toml
# Community Cloud 後台 Secrets 貼上，或本機放 .streamlit/secrets.toml
CWA_API_KEY = "你的中央氣象署授權碼"
```

程式端已用 `fetcher._get_api_key()` 同時相容兩種來源（雲端讀 `st.secrets`、本機讀環境變數/`.env`），不需為部署改程式碼。

### 2. 資料更新只能靠 app 內建（沒有 cron）

Community Cloud **不能跑背景排程 / cron**，也沒有持久磁碟。因此：
- **不要**依賴外部排程去更新資料庫（雲端根本沒有那個排程環境）。
- 由 `bootstrap.ensure_fresh_data()` 在 app 載入時判斷資料是否過舊並自動抓取，這是雲端唯一可行的更新方式，也正是決策 4 的用意。

### 3. SQLite 是暫存，容器休眠/重啟會清空

Community Cloud 的檔案系統是暫存的，App 一段時間沒人用會休眠，重啟後 `data.db` 會消失。對本專案的處理：
- 可接受：因為 `ensure_fresh_data()` 會在下次啟動時重新抓 CWA 資料重建 `data.db`。使用者第一次載入可能稍慢（要抓一次 API），屬正常。
- 若要資料持久或多人共享同一份，改接**雲端資料庫**（如 Turso/libSQL、Supabase Postgres），只需替換 `database.py` 的連線，其餘分層不動。

### 4. 依賴與 Python 版本

- `requirements.txt` 要完整列出所有套件（Cloud 依它安裝）。`python-dotenv` 只在本機需要；程式已用 try/except 讓雲端沒有它也不會壞。
- 需要特定系統套件時，另建 `packages.txt`（本專案通常不需要）。

### 5. 部署步驟

1. 程式碼 push 到 GitHub（見第十節）。
2. 到 https://share.streamlit.io 用 GitHub 登入，選這個 repo、分支與主程式 `app.py`。
3. 在 Settings → Secrets 貼上 `CWA_API_KEY`。
4. Deploy，取得公開網址即可分享。

### 6. `.gitignore` 必含

```
.env
.streamlit/secrets.toml
data.db
sample_response.json
__pycache__/
```

---

## 六、完整開發工作流程（步驟總覽）

> 順序刻意調整為「先確認真實資料 → 定義時段與資料表 → 完成解析與寫入驗證 → 服務 → 畫面 → 部署更新機制 → 最後加快取」，避免正確性問題。

1. **準備**：註冊 CWA 取得 API Key，寫入 `.env`（`CWA_API_KEY=...`）；`pip install -r requirements.txt`。
2. **取得真實 API 範例**：先跑一次抓取存成 `sample_response.json`，**核對欄位、時段、geocode**（決策 1）。
3. **定義時段與資料表**：依核對結果確定唯一鍵 `(geocode, startTime, endTime)`，完成 `database.py` schema。
4. **完成解析與寫入驗證**：完成 `fetcher.parse()`（按時間鍵配對 MinT/MaxT/**PoP 降雨機率**、缺值 None）；執行 `python update_data.py`，用 `SELECT DISTINCT county, town ...` 及每日彙整查詢驗證資料正確、`pop` 有值、重複執行不新增重複列。
5. **後端服務層**：完成 `service.py`，用簡單 script 測試各函式回傳正確。
6. **前端樣式**：完成 `styles.py`，確認玻璃背景與帶 key 容器樣式正常。
7. **前端元件**：完成 `components.py`（圖表、表格、地圖、**帶傘提醒 `umbrella_reminder`**，含空資料提示）。
8. **組裝**：完成 `bootstrap.py`，在 `app.py` 用 `service` 連結後端、顯示更新時間與預報時段；`streamlit run app.py` 本機驗證。
9. **決定部署後的更新機制**：確認 app 內建 `ensure_fresh_data`，讓部署環境自行更新（決策 4）。
10. **加快取**：對讀 DB / 抓 API 的函式加 `@st.cache_data`，**ttl 對齊更新頻率**（注意期限內會回舊值）。
11. **優化**（步驟 20）：錯誤處理、去重、註解、模組化。
12. **部署到 Community Cloud**（步驟 21、見五之二）：`.gitignore` 排除機密與 `data.db`，push 到 GitHub；在 Cloud 用 `st.secrets` 設定 `CWA_API_KEY`；靠 `ensure_fresh_data()` 更新資料。
13. **延伸**（步驟 22）：已加「帶傘提醒」；後續可再加旅遊/農業建議、Line Bot、AI 分析。

---

## 七、requirements.txt 建議內容

```
streamlit
requests
pandas
matplotlib
folium
streamlit-folium
python-dotenv        # 只有本機需要（讀 .env）；Community Cloud 用 st.secrets
# 架構 B 才需要：
# fastapi
# uvicorn
```

> `data/geo.py` 提供 `GEO_COORDS = {geocode: (lat, lng)}` 對照表（地圖用）。geocode 來自 CWA 資料，座標可用鄉鎮行政中心經緯度。

---

## 八、驗證檢查清單

- [ ] 已保存 `sample_response.json`，且 `parse()` 的欄位路徑與它一致（非憑欄位名推定）。
- [ ] `parse()` 按時間鍵配對 MinT/MaxT，缺值為 `None`（非 0），時段順序/數量不一致也不會錯位。
- [ ] `python update_data.py` 能成功寫入，且重複執行不新增重複列（`(geocode,startTime,endTime)` UNIQUE 生效，同日多時段不互相覆蓋）。
- [ ] `service.list_regions()` 用縣市+鄉鎮+geocode，不同縣市同名鄉鎮不混淆。
- [ ] 下拉選單切換地區時，折線圖與表格同步更新（用 geocode 查詢）。
- [ ] 日期選項來自資料庫實際有的日期；改變日期時地圖依當日彙整溫度更新。
- [ ] 首次啟動（空資料庫）時，`ensure_fresh_data()` 能建表並自動抓一次；API 失敗時顯示提示而非崩潰。
- [ ] 畫面顯示「資料最後更新時間」與「目前預報時段」；無資料時有明確提示。
- [ ] 快取 `ttl` 對齊更新頻率；理解期限內可能回舊值。
- [ ] `parse()` 有擷取降雨機率 `pop`，資料表 `pop` 欄位有值（用 sample 核對 PoP 的 elementName）。
- [ ] 帶傘提醒：某地區有時段 `pop > 50%` 時首頁顯示提醒；`pop` 缺值不觸發、不誤判為 0。
- [ ] 玻璃卡片用帶 key 的 `st.container()`，確實包住內部元件（非 div 夾）。
- [ ] 玻璃卡片在不同瀏覽器（Chrome/Safari）都能正確模糊（`backdrop-filter` 相容性）。
- [ ] 文字在半透明背景上對比度足夠（WCAG AA），帶傘提醒卡也是。
- [ ] Community Cloud：`CWA_API_KEY` 設在 st.secrets（非 .env）；App 重啟後能自動重抓重建資料。
- [ ] `.env`、`.streamlit/secrets.toml`、`data.db`、`sample_response.json` 未被 push 到 GitHub。

> 完整無障礙（WCAG）合規仍需以輔助科技實測與專家審查驗證。

---

## 相關文件
- 專案介紹：[README.md](./README.md)
- 設計與製作細節（24 步驟）：[design.md](./design.md)
