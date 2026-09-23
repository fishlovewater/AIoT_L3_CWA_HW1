# 設計文件：台灣天氣預報網站（Taiwan Weather Forecast）

本文件依據課程地圖「AI 創新微課程 — Taiwan Weather Forecast」的 24 個步驟撰寫，說明如何從零打造一個天氣預報網站。

**核心技術棧**：`CWA API × JSON × Python × Pandas × SQLite × Streamlit`

**整體製作流程**：
> 到中央氣象署（CWA）取得開放資料（用 Requests 呼叫 API）→ 解析 JSON、用 Pandas 處理 → 存進自建 SQLite 資料庫 → 用 SQL 查詢讀回 → 用 Streamlit 打造互動式 Web App（下拉選單、折線圖、資料表、地圖）→ 上傳 GitHub → 延伸應用。

**介面設計要求**：整個網站介面採用 **iOS 液態玻璃（Liquid Glass / Glassmorphism）** 風格 —— 半透明毛玻璃卡片、模糊背景、細緻邊框光暈與圓角，營造 iOS 26 質感。詳見「附錄 A：iOS 液態玻璃介面設計」。

---

## 重要設計決策（動工前先讀）

本專案在實作前確立了幾個關鍵決策，用來避免資料正確性問題。這些決策貫穿整份文件：

1. **先取得真實 API 範例，再定稿解析程式**：不可只憑欄位名稱推定 JSON 結構。務必先保存一份實際回應（見「三、資料擷取」的步驟 4.5），核對 `weatherElement` 實際有哪些 `elementName`、時間區間如何表示，再撰寫 `parse()`。

2. **保留原始預報時段（不做每日覆蓋）**：CWA 一週預報同一天可能有多個時段（例如每 12 小時一段）。本專案**保留原始時段**，資料表唯一鍵為 `(geocode, startTime, endTime)`，避免同日多筆互相覆蓋。若需要「每日高低溫」，另以 SQL 彙整（`MIN(minT)`、`MAX(maxT)` group by 日期），不改變底層資料粒度。

3. **地區以縣市 + 鄉鎮（＋行政區代碼）識別**：不可只用單一 `regionName`，否則不同縣市的同名鄉鎮會混淆。優先使用 CWA 提供的行政區代碼（`geocode`）作為穩定識別。

4. **部署與資料更新共用同一份資料、同一環境**：更新程式內建於 app（啟動時檢查 + 定時自動抓取），而非依賴外部本機排程去寫一份雲端拿不到的資料庫。SQLite 適合本機與課程展示；正式對外部署應改用雲端資料庫（見「十、部署」）。

5. **缺值與異常明確處理**：CWA 以特定值（或空字串）表示無觀測。解析與顯示時要轉為明確的「無資料」，不可當成數值。

6. **介面顯示資料版本資訊**：畫面需顯示「資料最後更新時間」「目前顯示的預報時段」「無資料提示」，讓使用者知道看到的是哪一版預報。

---

## 目錄（對應課程 24 步驟）

| # | 步驟 | 對應章節 |
|---|------|----------|
| 1 | 課程介紹 | 一、專案總覽 |
| 2 | 台灣的天氣與生活 | 一、專案總覽 |
| 3 | 中央氣象署 CWA Open Data 平台 | 二、資料來源 |
| 4 | API 資料取得（Requests） | 三、資料擷取 |
| 5 | JSON 資料結構解析 | 三、資料擷取 |
| 6 | 提取最高與最低氣溫 | 三、資料擷取 |
| 7 | 資料整理與預覽（Pandas） | 四、資料處理 |
| 8 | 建立 SQLite 資料庫 | 五、資料庫 |
| 9 | 資料庫設計（TemperatureForecasts） | 五、資料庫 |
| 10 | 查詢資料驗證（SQL） | 五、資料庫 |
| 11 | Streamlit 入門 | 六、Web App |
| 12 | 從資料庫讀取資料（SQL 查詢） | 六、Web App |
| 13 | 下拉選單選擇地區 | 七、功能實作 |
| 14 | 繪製折線圖（一週高低溫） | 七、功能實作 |
| 15 | 顯示資料表格 | 七、功能實作 |
| 16 | 整合 Web App 介面 | 七、功能實作 |
| 17 | 進階：台灣地圖視覺化（Folium） | 七、功能實作 |
| 18 | 選擇日期顯示地圖 | 七、功能實作 |
| 19 | 完整成果展示（Dashboard） | 八、整合展示 |
| 20 | 程式碼品質與優化 | 九、品質優化 |
| 21 | 專案上傳至 GitHub | 十、部署 |
| 22 | 延伸應用與想法 | 十一、延伸 |
| 23 | 回顧與重點整理 | 十二、總結 |
| 24 | 下一步：繼續探索 | 十二、總結 |

---

## 一、專案總覽（步驟 1、2）

### 步驟 1：課程介紹
- **目標**：用 Python 探索天氣、用程式看懂台灣、用 AI 實現更多可能。
- **成果**：一個可互動的天氣預報 Web App，含地區選擇、高低溫折線圖、資料表格與台灣地圖。
- **學習主軸**：AI × 資料 × 天氣 × 實作。

### 步驟 2：台灣的天氣與生活
- 天氣影響生活：出門穿著、農作、旅遊行程、防災決策。
- 用資料驅動決策，並延伸到智慧應用案例（Line 通知、農業、旅遊）。

### 系統架構圖

```
┌─────────────────────────────────────────────┐
│   中央氣象署 CWA Open Data API                 │
│   https://opendata.cwa.gov.tw                 │
└───────────────────┬─────────────────────────┘
                    │ ① Requests GET (帶授權碼)
                    ▼
        ┌───────────────────────────┐
        │  Python 擷取程式            │
        │  requests → JSON            │
        └───────────┬───────────────┘
                    │ ② 解析 JSON、提取高低溫
                    ▼
        ┌───────────────────────────┐
        │  Pandas DataFrame          │
        │  資料整理、清洗、預覽        │
        └───────────┬───────────────┘
                    │ ③ 寫入
                    ▼
        ┌───────────────────────────┐
        │  SQLite 資料庫 (data.db)    │
        │  TemperatureForecasts 表    │
        └───────────┬───────────────┘
                    │ ④ SQL 查詢讀回
                    ▼
        ┌───────────────────────────┐
        │  Streamlit Web App          │
        │  下拉選單 + 折線圖 +          │
        │  資料表 + Folium 地圖         │
        │  (iOS 液態玻璃介面)          │
        └───────────────────────────┘
```

---

## 二、資料來源：中央氣象署 CWA（步驟 3）

- **平台**：中央氣象署開放資料平台 `https://opendata.cwa.gov.tw`
- **製作步驟**：
  1. **註冊帳號**：到平台註冊會員（免費）。
  2. **取得 API Key**：於會員專區取得授權碼（Authorization Key）。
  3. **選擇資料集**：本專案使用「鄉鎮天氣預報 — 一週」資料集，內含各地區未來一週的最高溫（MaxT）與最低溫（MinT）。
- **常用資料集代碼**：
  | 代碼 | 內容 |
  |------|------|
  | `F-D0047-091` | 鄉鎮天氣預報（一週，各地區高低溫、降雨機率）|
  | `F-C0032-001` | 一般天氣預報（今明 36 小時，各縣市）|
- **API 基底**：`https://opendata.cwa.gov.tw/api/v1/rest/datastore/{資料集代碼}`
- **授權**：政府資料開放授權，免費可取得，使用時標示來源。

---

## 三、資料擷取：Requests + JSON（步驟 4、5、6）

### 步驟 4：API 資料取得（使用 Requests）

```python
import requests

url = 'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-091'
headers = {'Authorization': '你的_API_KEY'}
resp = requests.get(url, headers=headers, timeout=30)
resp.raise_for_status()
data = resp.json()
```

### 步驟 4.5：先保存一份真實 API 回應（必做，決策 1）

**在寫解析程式之前**，先把一份實際回應存成檔案，用它核對真實欄位與時間結構。不要憑欄位名稱推定 JSON 結構。

```python
import json
with open('sample_response.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

核對重點：
- `records` 底下實際的層級（不同資料集可能是 `records.locations[].location[]`，也可能是 `records.location[]`，以實際回應為準）。
- 每個 `location` 的 `weatherElement` **實際有哪些 `elementName`**（可能是 `MinT`/`MaxT`，也可能是 `T`、`Wx`、`PoP12h` 等，視資料集而定）。
- 每個 element 的 `time[]` **實際的時間欄位**：是 `startTime`/`endTime`，還是 `dataTime`？各 element 的時段是否對齊？
- 有無**行政區代碼**（如 `geocode`）可用來穩定識別地區。

### 步驟 5：JSON 資料結構解析

以核對後的實際結構為準（以下為常見結構，實作前請用步驟 4.5 的樣本確認）：

```
records
 └── locations[]                # 通常 [0] 為全臺
      ├── datasetDescription    # 資料說明
      └── location[]            # 各鄉鎮
           ├── locationName      # 鄉鎮名
           ├── geocode           # 行政區代碼（穩定識別，優先使用）
           └── weatherElement[]
                └── elementName  # 'MinT' / 'MaxT' / 'T' ...
                     └── time[]  # 各時段：startTime / endTime / elementValue
```

解析原則（呼應決策 1、2、5）：
- **按時間鍵配對，不用 `zip`**：把每個 element 的 time 依 `(startTime, endTime)` 建索引，再依相同時間鍵合併 MinT 與 MaxT。不同 element 的時段順序或數量不保證一致，用 `zip` 會錯位。
- **缺值明確處理**：某時段缺 MinT 或 MaxT、或值為空字串／非數字時，該欄位存 `None`（NULL），不要當 0。
- **保留原始時段**：每個 `(地區, startTime, endTime)` 就是一筆，不截成日期。

### 步驟 6：提取最高與最低氣溫（按時間鍵配對）

```python
def parse(data):
    """解析 CWA 一週預報，按時間鍵配對 MinT/MaxT，保留原始時段。
    回傳 list[dict]，缺值以 None 表示。實際欄位路徑請先用步驟 4.5 樣本核對。"""
    records = []
    locations = data['records']['locations'][0]['location']
    for loc in locations:
        county = data['records']['locations'][0].get('locationsName')  # 縣市層（視結構）
        town = loc['locationName']
        geocode = loc.get('geocode')  # 行政區代碼，優先作識別

        # 把每個 element 依時間鍵建索引
        elem_by_name = {e['elementName']: e for e in loc['weatherElement']}
        mint_times = _index_by_time(elem_by_name.get('MinT'))
        maxt_times = _index_by_time(elem_by_name.get('MaxT'))

        # 以兩者時間鍵的聯集配對
        all_keys = sorted(set(mint_times) | set(maxt_times))
        for key in all_keys:
            start_time, end_time = key
            records.append({
                'geocode': geocode,
                'county': county,
                'town': town,
                'startTime': start_time,
                'endTime': end_time,
                'minT': _to_int(mint_times.get(key)),   # 缺值 → None
                'maxT': _to_int(maxt_times.get(key)),
            })
    return records


def _index_by_time(element):
    """把一個 weatherElement 的 time[] 轉成 {(startTime, endTime): value}。"""
    result = {}
    if not element:
        return result
    for t in element['time']:
        key = (t.get('startTime'), t.get('endTime') or t.get('startTime'))
        value = t['elementValue'][0]['value'] if t.get('elementValue') else None
        result[key] = value
    return result


def _to_int(v):
    """轉整數；空值或非數字回傳 None，避免把缺值當 0。"""
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
```

> 注意：上面 `county` / 欄位路徑以常見結構示意。**務必先用步驟 4.5 的 `sample_response.json` 確認**縣市層在哪一層、`geocode` 是否存在，再定稿此函式。

---

## 四、資料處理：Pandas（步驟 7）

### 步驟 7：資料整理與預覽

把擷取的資料轉成 Pandas DataFrame，方便清洗與檢視：

```python
import pandas as pd

df = pd.DataFrame(records)
print(df.head())
```

預覽結果（範例，保留原始時段、含縣市與鄉鎮）：

| geocode | county | town | startTime | endTime | minT | maxT |
|---------|--------|------|-----------|---------|------|------|
| 6300500 | 臺北市 | 中正區 | 2026-04-14 06:00 | 2026-04-14 18:00 | 20 | 26 |
| 6300500 | 臺北市 | 中正區 | 2026-04-14 18:00 | 2026-04-15 06:00 | 18 | 22 |
| 6600400 | 臺中市 | 西屯區 | 2026-04-14 06:00 | 2026-04-14 18:00 | 21 | 30 |

處理重點：
- 時間欄位保留原始 `startTime` / `endTime`（不截成日期），符合決策 2。
- 型別轉換：溫度轉整數，缺值保持 `None`（不要 `fillna(0)`）。
- 以 `(geocode, startTime, endTime)` 判斷重複。
- 需要「每日高低溫」時，另用 SQL 彙整（見步驟 10），不改底層粒度。

---

## 五、資料庫：SQLite（步驟 8、9、10）

### 步驟 8：建立 SQLite 資料庫（儲存氣溫資料）

```python
import sqlite3
conn = sqlite3.connect('data.db')
```
- 建立資料庫檔 `data.db`
- 建立資料表
- 插入氣溫資料

### 步驟 9：資料庫設計 — `TemperatureForecasts` 表

唯一鍵改為 `(geocode, startTime, endTime)`，保留原始時段、以行政區代碼穩定識別（決策 2、3）。同時保存資料抓取時間，供畫面顯示「最後更新時間」（決策 6）。

```sql
CREATE TABLE IF NOT EXISTS TemperatureForecasts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    geocode    TEXT,              -- 行政區代碼（穩定識別）
    county     TEXT,              -- 縣市
    town       TEXT,              -- 鄉鎮
    startTime  TEXT,              -- 時段起（原始，不截成日期）
    endTime    TEXT,              -- 時段訖
    minT       REAL,              -- 可為 NULL（缺值）
    maxT       REAL,              -- 可為 NULL（缺值）
    fetchedAt  TEXT,              -- 本筆資料抓取時間（ISO8601）
    UNIQUE (geocode, startTime, endTime)
);
```

**寫入用 upsert，不要用 `to_sql(if_exists='replace')`**（後者會砍掉整表與唯一鍵約束）：

```python
def save(conn, records, fetched_at):
    conn.executemany("""
        INSERT INTO TemperatureForecasts
            (geocode, county, town, startTime, endTime, minT, maxT, fetchedAt)
        VALUES (:geocode, :county, :town, :startTime, :endTime, :minT, :maxT, :fetchedAt)
        ON CONFLICT(geocode, startTime, endTime) DO UPDATE SET
            minT=excluded.minT, maxT=excluded.maxT, fetchedAt=excluded.fetchedAt
    """, [{**r, 'fetchedAt': fetched_at} for r in records])
    conn.commit()
```

### 步驟 10：查詢資料驗證（SQL）

```sql
-- 取得所有地區（用縣市+鄉鎮，避免同名混淆）
SELECT DISTINCT county, town, geocode FROM TemperatureForecasts ORDER BY county, town;

-- 查詢特定地區的原始時段預報
SELECT startTime, endTime, minT, maxT
FROM TemperatureForecasts
WHERE geocode = '6300500'
ORDER BY startTime;

-- 每日高低溫彙整（決策 2：需要每日視圖時用）
SELECT substr(startTime, 1, 10) AS day,
       MIN(minT) AS dayMin,
       MAX(maxT) AS dayMax
FROM TemperatureForecasts
WHERE geocode = '6300500'
GROUP BY day
ORDER BY day;

-- 可用日期清單（給日期選擇器用，決策：日期選項來自現有資料）
SELECT DISTINCT substr(startTime, 1, 10) AS day
FROM TemperatureForecasts ORDER BY day;
```

---

## 六、Web App：Streamlit（步驟 11、12）

### 步驟 11：Streamlit 入門

- **安裝環境**：`pip install streamlit`
- **基本結構**：
  ```python
  import streamlit as st
  st.title("Taiwan Weather Forecast")
  st.write("Hello World")
  ```
- **啟動**：`streamlit run app.py`

### 步驟 12：從資料庫讀取資料（SQL 查詢）

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('data.db')
df = pd.read_sql_query('SELECT * FROM TemperatureForecasts', conn)
```

---

## 七、功能實作（步驟 13–18）

以下每個功能都說明：**需要什麼資料 → 從哪取得 → 如何製作**。所有 UI 元件皆套用 iOS 液態玻璃樣式（見附錄 A）。

### 功能 1（步驟 13）：下拉選單選擇地區

- **需要的資料**：縣市 + 鄉鎮清單（用 geocode 識別，避免同名混淆）。
- **資料來源**：`SELECT DISTINCT county, town, geocode FROM TemperatureForecasts`。
- **如何製作**：顯示「縣市 鄉鎮」，實際用 geocode 查詢。
  ```python
  regions = service.list_regions()   # [{'label':'臺北市 中正區','geocode':'6300500'}, ...]
  labels = [r['label'] for r in regions]
  idx = st.selectbox('選擇地區', range(len(labels)), format_func=lambda i: labels[i])
  geocode = regions[idx]['geocode']
  ```

### 功能 2（步驟 14）：繪製折線圖（一週最高最低溫）

- **需要的資料**：選定地區的時段序列 `startTime`、`minT`、`maxT`。
- **資料來源**：`service.get_region_week(geocode)`（保留原始時段）。
- **如何製作**：以時段起始時間為 X 軸，畫兩條線（MaxT、MinT）。缺值的點自動斷開。
  ```python
  import matplotlib.pyplot as plt
  fig, ax = plt.subplots()
  ax.plot(df['startTime'], df['maxT'], marker='o', label='MaxT')
  ax.plot(df['startTime'], df['minT'], marker='o', label='MinT')
  ax.legend(); fig.autofmt_xdate()
  st.pyplot(fig)
  ```
  若要「每日」視圖，改用每日彙整查詢（步驟 10）當資料來源。

### 功能 3（步驟 15）：顯示資料表格

- **需要的資料**：選定地區的時段資料（時段、MinT、MaxT）。
- **資料來源**：同功能 2 的 DataFrame。
- **如何製作**：
  ```python
  st.dataframe(df[['startTime', 'endTime', 'minT', 'maxT']],
               use_container_width=True)
  ```

### 功能 4（步驟 16）：整合 Web App 介面

- 把「下拉選單 + 折線圖 + 資料表」整合到同一頁面，並在頂部顯示**資料最後更新時間**與**目前顯示的預報時段範圍**（決策 6）。
- 版面：標題（含更新時間）→ 地區選擇 → 折線圖 → 資料表，各區以液態玻璃容器分區（用 `st.container()`，見附錄 A.2）。

### 功能 5（步驟 17）：進階 — 台灣地圖視覺化（Folium）

- **需要的資料**：各地區座標（經緯度）+ 該地區溫度；平均溫度分級顏色。
- **資料來源**：座標用 `geocode → (lat, lng)` 對照表（`data/geo.py`）；溫度來自資料庫每日彙整查詢。用 geocode 對座標，避免同名鄉鎮對錯位置。
- **如何製作**：用 Folium 畫台灣地圖，依平均溫度上色。缺座標或缺值的點略過。
  | 平均溫度 | 顏色 |
  |----------|------|
  | < 20°C | 藍 |
  | 20–25°C | 綠 |
  | 25–30°C | 橙 |
  | > 30°C | 紅 |
  ```python
  import folium
  from streamlit_folium import st_folium
  from data.geo import GEO_COORDS   # {geocode: (lat, lng)}

  m = folium.Map(location=[23.7, 121], zoom_start=7)
  for row in day_df.itertuples():
      coord = GEO_COORDS.get(row.geocode)
      if not coord or row.minT is None or row.maxT is None:
          continue
      avg = (row.minT + row.maxT) / 2
      folium.CircleMarker(
          location=coord, radius=10, fill=True,
          color=color_by_temp(avg),
          popup=f"{row.county} {row.town}: {avg:.0f}°C"
      ).add_to(m)
  st_folium(m)
  ```

### 功能 6（步驟 18）：選擇日期顯示地圖

- **需要的資料**：某一日各地區的溫度（以每日彙整）。
- **資料來源**：可用日期清單 + 該日彙整查詢（見步驟 10）。
- **如何製作**：**日期選項來自資料庫實際有的日期**（避免預設今天但資料庫沒有而空白）。
  ```python
  available_days = service.available_days()      # 從 DB 取實際有的日期
  if not available_days:
      st.warning('目前沒有可用的預報資料，請先更新資料。')
  else:
      day = st.selectbox('選擇日期', available_days)  # 用 selectbox 限定有資料的日期
      day_df = service.get_day_all_regions(day)
      if day_df.empty:
          st.info(f'{day} 沒有預報資料。')
      else:
          ui.taiwan_map(day_df)
  ```

---

## 八、整合展示（步驟 19）

### 步驟 19：完整成果展示 — Taiwan Weather Dashboard

把所有元件組成一個完整的 Dashboard：
- 頂部標題（液態玻璃橫幅）
- 地區下拉選單 + 日期選擇器
- 一週高低溫折線圖
- 資料表格
- 台灣地圖（依日期／溫度上色）

版面採卡片式分區，全部套用 iOS 液態玻璃樣式。

---

## 九、程式碼品質與優化（步驟 20）

- **程式結構清晰**：擷取、處理、資料庫、UI 分成不同函式／模組。
- **錯誤處理機制**：API 逾時、JSON 結構改變、缺值都要 try/except 處理。
- **重複執行不重複插入**：用唯一鍵 `(geocode, startTime, endTime)` + upsert（`ON CONFLICT ... DO UPDATE`），不要用 `to_sql(if_exists='replace')`（會砍掉整表與約束）。
- **良好的註解**：關鍵邏輯加上說明。

```python
def fetch_forecast():
    """呼叫 CWA API，回傳整理後的 DataFrame。"""
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return parse(resp.json())
    except requests.RequestException as e:
        st.error(f"資料取得失敗：{e}")
        return pd.DataFrame()
```

---

## 十、部署與資料更新（步驟 21）

### 步驟 21：版本管理與備份

1. **建立 Repository**：在 GitHub 建立新 repo。
2. **連結 Git（remote）**：
   ```bash
   git init
   git remote add origin https://github.com/你的帳號/taiwan-weather.git
   ```
3. **Commit & Push**：
   ```bash
   git add .
   git commit -m "Taiwan Weather Forecast app"
   git push -u origin main
   ```
- `.gitignore` 排除 `data.db`、`.env`、`sample_response.json`。

### 部署與更新機制（決策 4：兩者共用同一份資料、同一環境）

關鍵原則：**更新資料的程式，要跑在「網站讀取資料的同一個環境」**。本機排程更新本機 `data.db`，並不會更新雲端那份，兩者是不同檔案。因此把更新內建到 app：

**做法：app 自行更新（推薦第一版）**
- app 啟動時先 `init_db()`，若資料庫為空或 `fetchedAt` 過舊，就自行呼叫一次更新。
- 之後每次使用者互動時，用快取控制更新頻率（快取過期才重新抓 API 寫入）。
- 這樣不論部署在本機或雲端，資料更新都與網站在同一環境、共用同一份資料。

```python
def ensure_fresh_data(max_age_hours=6):
    """app 啟動 / 互動時呼叫：資料太舊或不存在就自行更新。"""
    database.init_db()
    last = database.last_fetched_at()   # 讀 max(fetchedAt)
    if last is None or _older_than(last, max_age_hours):
        update_data.run()               # 抓 API → 寫入同一份 DB
```

**部署選項比較**

| 部署方式 | 資料儲存 | 更新方式 | 注意 |
|----------|----------|----------|------|
| 本機執行 | 本機 `data.db` | app 內建更新 或 本機排程（同機） | 適合開發／課堂展示 |
| Streamlit Community Cloud | 容器內 `data.db`（**暫存，重啟即消失**）| app 內建更新（啟動時重抓）| 免費、簡單；資料非持久 |
| 雲端主機 + 雲端資料庫 | 外部 Postgres / Turso 等 | app 內建更新 或 雲端排程 | 正式對外部署建議此法，資料才持久 |

> 重點：SQLite 在 Community Cloud 只是暫存檔，容器重啟就清空。課程展示可接受（靠 app 啟動時重抓）；若要資料持久或多人共用，改用雲端資料庫（如 Turso/libSQL 或 Postgres），把 `database.py` 的連線換掉即可，其餘分層不變。

---

## 十一、延伸應用與想法（步驟 22）

從天氣預報衍生更多可能：
- **天氣提醒 Line Bot**：每天推播明日高低溫與降雨提醒。
- **旅遊行程建議**：依天氣推薦行程。
- **農業／防災應用**：低溫特報通知農友、豪雨預警。
- **結合 AI 分析**：用 AI 產生穿著建議、活動建議或天氣趨勢摘要。

---

## 十二、總結（步驟 23、24）

### 步驟 23：回顧與重點整理（你學會了什麼）
- ✅ API 資料取得（Requests）
- ✅ JSON 資料解析
- ✅ SQLite 資料庫（建表、寫入、查詢）
- ✅ Streamlit Web App
- ✅ AI × Coding 完整流程

### 步驟 24：下一步 — 繼續探索
- AI × Data × Real World
- 更多公開資料的串接與應用
- AI 輔助開發、把資料變成智慧應用
- 用程式打造更好的台灣

---

## 附錄 A：iOS 液態玻璃介面設計（Liquid Glass / Glassmorphism）

整站 UI 採 iOS 26「液態玻璃」風格。核心視覺元素：半透明背景、背景模糊（backdrop blur）、細白邊框、柔和陰影、大圓角、細緻高光。

### A.1 在 Streamlit 注入自訂 CSS

Streamlit 可用 `st.markdown(..., unsafe_allow_html=True)` 注入 CSS，把預設元件包成玻璃卡片：

```python
import streamlit as st

st.markdown("""
<style>
/* 頁面背景：柔和漸層，讓玻璃感更明顯 */
.stApp {
    background: linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 50%, #d4fc79 100%);
    background-attachment: fixed;
}

/* 液態玻璃卡片 */
.glass-card {
    background: rgba(255, 255, 255, 0.15);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.35);
    border-radius: 24px;
    box-shadow: 0 8px 32px rgba(31, 38, 135, 0.2);
    padding: 20px 24px;
    margin-bottom: 18px;
}

/* 標題玻璃橫幅 */
.glass-header {
    background: rgba(255, 255, 255, 0.25);
    backdrop-filter: blur(30px);
    border-radius: 28px;
    border: 1px solid rgba(255,255,255,0.4);
    padding: 24px;
    text-align: center;
}

/* 下拉選單、資料表也套玻璃感 */
div[data-baseweb="select"] > div,
.stDataFrame {
    background: rgba(255,255,255,0.18) !important;
    backdrop-filter: blur(12px);
    border-radius: 16px !important;
    border: 1px solid rgba(255,255,255,0.3);
}
</style>
""", unsafe_allow_html=True)
```

### A.2 用玻璃卡片包住每個區塊（正確做法）

**不要**用兩次 `st.markdown` 輸出開、關 `<div>` 去夾中間的元件——Streamlit 會把 HTML 與元件各自獨立渲染，`<div>` 包不住中間的 selectbox／圖表。

正確做法：用**帶 `key` 的 `st.container()`**，再用 CSS 針對該容器的自動屬性（`.st-key-<key>`）套玻璃樣式。這樣容器內的所有元件都會被真正包在同一張卡片裡。

```python
# CSS：針對帶 key 的容器上玻璃樣式（Streamlit 會產生 class st-key-<key>）
st.markdown("""
<style>
.st-key-region_card, .st-key-chart_card, .st-key-map_card {
    background: rgba(255,255,255,0.15);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(255,255,255,0.35);
    border-radius: 24px;
    box-shadow: 0 8px 32px rgba(31,38,135,0.2);
    padding: 20px 24px;
}
</style>
""", unsafe_allow_html=True)

# 用 key 的 container 真正包住元件
with st.container(key="region_card"):
    selected = st.selectbox('選擇地區', labels)

with st.container(key="chart_card"):
    ui.temperature_chart(week_df)
```

> `st.container(key=...)` 產生的 CSS class 形如 `st-key-region_card`。若 Streamlit 版本的 class 命名不同，用瀏覽器開發者工具確認實際 class 再調整選擇器。

### A.3 設計規範（Design Tokens）

| 項目 | 值 |
|------|-----|
| 卡片背景 | `rgba(255,255,255,0.15)` |
| 背景模糊 | `blur(20px) saturate(180%)` |
| 邊框 | `1px solid rgba(255,255,255,0.35)` |
| 圓角 | 卡片 24px、橫幅 28px、小元件 16px |
| 陰影 | `0 8px 32px rgba(31,38,135,0.2)` |
| 頁面背景 | 淺色漸層（藍→青→綠），突顯玻璃透明感 |
| 字體 | 系統字體（-apple-system, "SF Pro"），深色文字確保對比 |

### A.4 無障礙（Accessibility）注意
- 玻璃是半透明的，文字要維持足夠對比度（WCAG AA，至少 4.5:1）——必要時在文字後方加深色半透明底。
- 模糊效果不影響鍵盤操作與螢幕閱讀器；所有互動元件保留 focus 樣式。
- 提供可關閉動態／模糊的偏好（尊重 `prefers-reduced-motion`）。

> 完整 WCAG 合規需以輔助科技實測與專家審查驗證。

---

## 附錄 B：資料來源與授權

- 中央氣象署開放資料平台：https://opendata.cwa.gov.tw
- 政府資料開放平台：https://data.gov.tw
- Streamlit：https://streamlit.io
- Folium：https://python-visualization.github.io/folium/
- OpenStreetMap 圖磚（Folium 預設，免費）：https://www.openstreetmap.org

資料採政府資料開放授權，免費取得，使用時請標示來源。實際欄位與資料集代碼請以官方平台最新公告為準；內容已改寫整理以符合資料授權規範。
