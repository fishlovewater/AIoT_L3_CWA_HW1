# 開發工作流程文件（Workflow）：台灣天氣預報網站

本文件依據 [design.md](./design.md) 撰寫，說明這個專案「有哪些功能、每個功能怎麼做」，並特別著重在**前端、後端，以及前後端如何連結**。

技術棧：`CWA API × Python × Requests × Pandas × SQLite × Streamlit（+ Folium）`，介面採 iOS 液態玻璃風格。

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
│   └── geo.py              # 各地區經緯度對照表（給地圖用）
├── data.db                 # SQLite 資料庫（不進版控）
├── requirements.txt
├── .env                    # API Key（不進版控）
├── .gitignore
└── update_data.py          # 排程用：定時抓資料寫入 DB
```

分層原則（呼應 design.md「程式結構清晰」）：
- **後端（backend/）**：只負責「拿資料、處理資料、存取資料庫」，不碰任何 UI。
- **前端（frontend/ + app.py）**：只負責「排版、樣式、把資料畫出來」，不直接寫 SQL。
- 兩者透過 `backend/service.py` 這一層乾淨的函式介面連結。

---

## 三、後端（Backend）：資料層與邏輯層

後端負責 design.md 的步驟 3–10、20。分三個模組。

### 3.1 `fetcher.py` — 從 CWA 取得並解析資料（步驟 4、5、6）

職責：呼叫 CWA API → 解析巢狀 JSON → 提取 MinT / MaxT → 回傳乾淨的 list。

```python
# backend/fetcher.py
import os, requests

BASE = 'https://opendata.cwa.gov.tw/api/v1/rest/datastore'
DATASET = 'F-D0047-091'   # 鄉鎮天氣預報（一週）

def fetch_raw():
    """呼叫 CWA API，回傳原始 JSON。"""
    url = f'{BASE}/{DATASET}'
    headers = {'Authorization': os.environ['CWA_API_KEY']}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()

def parse(data):
    """解析 JSON，提取各地區一週高低溫。回傳 list[dict]。"""
    records = []
    for loc in data['records']['locations'][0]['location']:
        region = loc['locationName']
        mint = next(e for e in loc['weatherElement'] if e['elementName'] == 'MinT')
        maxt = next(e for e in loc['weatherElement'] if e['elementName'] == 'MaxT')
        for mt, xt in zip(mint['time'], maxt['time']):
            records.append({
                'regionName': region,
                'dataDate': mt['startTime'][:10],
                'minT': int(mt['elementValue'][0]['value']),
                'maxT': int(xt['elementValue'][0]['value']),
            })
    return records
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
                regionName TEXT,
                dataDate   TEXT,
                minT REAL,
                maxT REAL,
                UNIQUE(regionName, dataDate)   -- 步驟 20：避免重複插入
            )
        """)

def save(records):
    """寫入資料，重複的 (地區,日期) 會被覆蓋而非重複新增。"""
    with get_conn() as conn:
        conn.executemany("""
            INSERT INTO TemperatureForecasts (regionName, dataDate, minT, maxT)
            VALUES (:regionName, :dataDate, :minT, :maxT)
            ON CONFLICT(regionName, dataDate)
            DO UPDATE SET minT=excluded.minT, maxT=excluded.maxT
        """, records)

def query_df(sql, params=()):
    """執行查詢，回傳 DataFrame。"""
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)
```

### 3.3 `service.py` — 對前端暴露的資料服務（前後端的連結點）

這一層是**前端唯一會呼叫的後端入口**。前端不直接寫 SQL、不直接碰 requests，只呼叫這裡的函式。這就是架構 A 中「前後端連結」的關鍵介面。

```python
# backend/service.py
from . import database as db

def list_regions():
    """給下拉選單用：回傳所有地區名稱。"""
    return db.query_df(
        "SELECT DISTINCT regionName FROM TemperatureForecasts"
    )['regionName'].tolist()

def get_region_week(region):
    """給折線圖 / 表格用：某地區一週高低溫。"""
    return db.query_df(
        "SELECT dataDate, minT, maxT FROM TemperatureForecasts "
        "WHERE regionName = ? ORDER BY dataDate", (region,))

def get_day_all_regions(date):
    """給地圖用：某一天所有地區的溫度。"""
    return db.query_df(
        "SELECT regionName, minT, maxT FROM TemperatureForecasts "
        "WHERE dataDate = ?", (str(date),))
```

### 3.4 資料更新流程 `update_data.py`（步驟 7、20）

把「抓 → 解析 → 存」串起來，可手動執行或排程。

```python
# update_data.py
from backend import fetcher, database

def run():
    database.init_db()
    raw = fetcher.fetch_raw()      # 步驟 4
    records = fetcher.parse(raw)   # 步驟 5、6
    database.save(records)         # 步驟 8、9
    print(f"已更新 {len(records)} 筆資料")

if __name__ == '__main__':
    run()
```

排程（每天更新）：Windows 用「工作排程器」呼叫 `python update_data.py`；Linux 用 cron。

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
    </style>
    """, unsafe_allow_html=True)
```

### 4.2 `components.py` — 可重用 UI 元件

```python
# frontend/components.py
import streamlit as st
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
from data.geo import REGION_COORDS

def glass_open(): st.markdown('<div class="glass-card">', unsafe_allow_html=True)
def glass_close(): st.markdown('</div>', unsafe_allow_html=True)

def temperature_chart(df):
    """折線圖（步驟 14）。"""
    fig, ax = plt.subplots()
    ax.plot(df['dataDate'], df['maxT'], marker='o', label='MaxT')
    ax.plot(df['dataDate'], df['minT'], marker='o', label='MinT')
    ax.legend(); ax.set_xlabel('Date'); ax.set_ylabel('°C')
    st.pyplot(fig)

def data_table(df):
    """資料表（步驟 15）。"""
    st.dataframe(df, use_container_width=True)

def taiwan_map(day_df):
    """Folium 地圖（步驟 17、18）。"""
    m = folium.Map(location=[23.7, 121], zoom_start=7)
    for _, row in day_df.iterrows():
        coord = REGION_COORDS.get(row['regionName'])
        if not coord:
            continue
        avg = (row['minT'] + row['maxT']) / 2
        folium.CircleMarker(
            location=coord, radius=10, fill=True,
            color=_color_by_temp(avg),
            popup=f"{row['regionName']}: {avg:.0f}°C"
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
| 下拉選單選地區 | 13 | `st.selectbox` | `service.list_regions()` |
| 一週高低溫折線圖 | 14 | `temperature_chart()` | `service.get_region_week()` |
| 資料表格 | 15 | `data_table()` | `service.get_region_week()` |
| 台灣地圖 | 17 | `taiwan_map()` | `service.get_day_all_regions()` |
| 日期選地圖 | 18 | `st.date_input` | `service.get_day_all_regions()` |

---

## 五、前後端如何連結（重點）

### 5.1 架構 A：函式呼叫連結（本專案主線）

`app.py` 是前端入口。它 **import 後端 service**，用函式呼叫取得資料，再交給前端元件畫出來。連結媒介是「Python 函式的參數與回傳值（DataFrame）」，不需要 HTTP。

```python
# app.py — 前端組裝，透過 service 連結後端
import streamlit as st
from backend import service                 # ← 連結後端的唯一入口
from frontend.styles import inject_glass_css
from frontend import components as ui

st.set_page_config(page_title="Taiwan Weather Forecast", layout="wide")
inject_glass_css()                          # 套用玻璃樣式

# 標題（玻璃橫幅）
st.markdown('<div class="glass-header"><h1>Taiwan Weather Forecast</h1></div>',
            unsafe_allow_html=True)

# --- 控制列：地區 + 日期 ---
ui.glass_open()
col1, col2 = st.columns(2)
with col1:
    regions = service.list_regions()        # 後端 → 前端
    region = st.selectbox('選擇地區', regions)
with col2:
    date = st.date_input('選擇日期')
ui.glass_close()

# --- 折線圖 ---
week_df = service.get_region_week(region)   # 後端 → 前端
ui.glass_open()
st.subheader(f'{region} 一週高低溫')
ui.temperature_chart(week_df)
ui.glass_close()

# --- 資料表 ---
ui.glass_open()
ui.data_table(week_df)
ui.glass_close()

# --- 地圖 ---
day_df = service.get_day_all_regions(date)  # 後端 → 前端
ui.glass_open()
st.subheader(f'{date} 全台溫度地圖')
ui.taiwan_map(day_df)
ui.glass_close()
```

**連結流程（一次使用者互動）**：
1. 使用者在瀏覽器改變下拉選單 →
2. Streamlit 透過 WebSocket 通知伺服器，**從頭重跑 `app.py`** →
3. `app.py` 呼叫 `service.get_region_week(region)`（前端 → 後端）→
4. `service` 呼叫 `database.query_df` 查 SQLite，回傳 DataFrame（後端 → 前端）→
5. 前端元件把 DataFrame 畫成玻璃卡片內的圖表 →
6. Streamlit 把新畫面推回瀏覽器。

> 效能提醒：Streamlit 每次互動都重跑整支程式，因此對「讀資料庫」「抓 API」這類昂貴操作要用快取：
> ```python
> @st.cache_data(ttl=600)   # 快取 10 分鐘
> def cached_week(region):
>     return service.get_region_week(region)
> ```

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

---

## 六、完整開發工作流程（步驟總覽）

1. **準備**：註冊 CWA 取得 API Key，寫入 `.env`（`CWA_API_KEY=...`）；`pip install -r requirements.txt`。
2. **後端資料層**：完成 `fetcher.py`（抓+解析）、`database.py`（建表+存+查）。
3. **灌資料**：執行 `python update_data.py`，確認 `data.db` 有資料（`SELECT DISTINCT regionName ...` 驗證）。
4. **後端服務層**：完成 `service.py`，用簡單 script 測試三個函式回傳正確。
5. **前端樣式**：完成 `styles.py`，確認玻璃背景與卡片正常。
6. **前端元件**：完成 `components.py`（圖表、表格、地圖）。
7. **組裝**：在 `app.py` 用 `service` 連結後端、用元件呈現；`streamlit run app.py` 本機驗證。
8. **加快取**：對讀 DB / 抓 API 的函式加 `@st.cache_data`。
9. **優化**（步驟 20）：加錯誤處理、去重、註解、模組化。
10. **部署**（步驟 21）：`.gitignore` 排除 `data.db` 與 `.env`，push 到 GitHub，可上 Streamlit Community Cloud。
11. **排程更新**：設定工作排程器 / cron 定時跑 `update_data.py`。
12. **延伸**（步驟 22）：Line Bot 推播、旅遊/農業建議、AI 分析。

---

## 七、requirements.txt 建議內容

```
streamlit
requests
pandas
matplotlib
folium
streamlit-folium
python-dotenv
# 架構 B 才需要：
# fastapi
# uvicorn
```

---

## 八、驗證檢查清單

- [ ] `python update_data.py` 能成功寫入資料，且重複執行不會重複新增（UNIQUE 生效）。
- [ ] `service.list_regions()` 回傳所有地區。
- [ ] 下拉選單切換地區時，折線圖與表格同步更新。
- [ ] 日期選擇改變時，地圖顏色依當日溫度更新。
- [ ] 玻璃卡片在不同瀏覽器（Chrome/Safari）都能正確模糊（`backdrop-filter` 相容性）。
- [ ] 文字在半透明背景上對比度足夠（WCAG AA）。
- [ ] `.env` 與 `data.db` 未被 push 到 GitHub。

> 完整無障礙（WCAG）合規仍需以輔助科技實測與專家審查驗證。

---

## 相關文件
- 專案介紹：[README.md](./README.md)
- 設計與製作細節（24 步驟）：[design.md](./design.md)
