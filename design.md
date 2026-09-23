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

2. **保留原始預報時段（不做每日覆蓋）**：CWA 一週預報同一天可能有多個時段（例如每 12 小時一段）。本專案**保留原始時段**，資料表唯一鍵為 `(county, town, startTime, endTime)`，避免同日多筆互相覆蓋。若需要「每日高低溫」，另以 SQL 彙整（`MIN(minT)`、`MAX(maxT)` group by 日期），不改變底層資料粒度。

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

```sql
CREATE TABLE IF NOT EXISTS TemperatureForecasts (
    id          INTEGER PRIMARY KEY,
    regionName  TEXT,
    dataDate    TEXT,
    minT        REAL,
    maxT        REAL
);
```

寫入資料（用 Pandas 直接寫入）：
```python
df.to_sql('TemperatureForecasts', conn, if_exists='replace', index=False)
```

### 步驟 10：查詢資料驗證（SQL）

驗證資料是否正確寫入：
```sql
-- 取得所有地區名稱
SELECT DISTINCT regionName FROM TemperatureForecasts;

-- 查詢特定地區
SELECT * FROM TemperatureForecasts WHERE regionName = '中部地區';
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

- **需要的資料**：所有地區名稱清單。
- **資料來源**：`SELECT DISTINCT regionName FROM TemperatureForecasts`。
- **如何製作**：
  ```python
  regions = df['regionName'].unique()
  selected = st.selectbox('Select Region', regions)
  filtered = df[df['regionName'] == selected]
  ```
- 下拉選單以液態玻璃卡片包覆。

### 功能 2（步驟 14）：繪製折線圖（一週最高最低溫）

- **需要的資料**：選定地區未來一週的 `dataDate`、`minT`、`maxT`。
- **資料來源**：由步驟 13 過濾後的 DataFrame。
- **如何製作**：以日期為 X 軸，畫兩條線（MaxT、MinT）。
  ```python
  import matplotlib.pyplot as plt
  fig, ax = plt.subplots()
  ax.plot(filtered['dataDate'], filtered['maxT'], marker='o', label='MaxT')
  ax.plot(filtered['dataDate'], filtered['minT'], marker='o', label='MinT')
  ax.legend()
  st.pyplot(fig)
  ```
  （亦可用 `st.line_chart(filtered.set_index('dataDate')[['maxT','minT']])`。）

### 功能 3（步驟 15）：顯示資料表格

- **需要的資料**：選定地區的一週資料（Date、MinT、MaxT）。
- **資料來源**：過濾後的 DataFrame。
- **如何製作**：
  ```python
  st.dataframe(filtered[['dataDate', 'minT', 'maxT']])
  ```
- 表格外層以毛玻璃容器呈現，清楚呈現一週資料。

### 功能 4（步驟 16）：整合 Web App 介面

- 把「下拉選單 + 折線圖 + 資料表」整合到同一頁面。
- 版面：標題 → 地區選擇 → 折線圖 → 資料表，全部以液態玻璃卡片分區。

### 功能 5（步驟 17）：進階 — 台灣地圖視覺化（Folium）

- **需要的資料**：各地區的代表座標（經緯度）+ 該地區溫度；平均溫度分級顏色。
- **資料來源**：地區座標可自建對照表（地區名 → lat/lng）；溫度來自資料庫。
- **如何製作**：用 Folium 畫台灣地圖，依平均溫度上色。
  | 平均溫度 | 顏色 |
  |----------|------|
  | < 20°C | 藍 |
  | 20–25°C | 綠 |
  | 25–30°C | 橙 |
  | > 30°C | 紅 |
  ```python
  import folium
  from streamlit_folium import st_folium
  m = folium.Map(location=[23.7, 121], zoom_start=7)
  for _, row in geo_df.iterrows():
      folium.CircleMarker(
          location=[row['lat'], row['lng']],
          radius=10, color=color_by_temp(row['avgT']),
          fill=True, popup=f"{row['regionName']}: {row['avgT']}°C"
      ).add_to(m)
  st_folium(m)
  ```

### 功能 6（步驟 18）：選擇日期顯示地圖

- **需要的資料**：某一日各地區的溫度。
- **資料來源**：`SELECT * FROM TemperatureForecasts WHERE dataDate = ?`。
- **如何製作**：加一個日期選擇器，選定日期後更新地圖顏色。
  ```python
  date = st.date_input('Select Date')
  day_df = df[df['dataDate'] == str(date)]
  # 依 day_df 重新繪製地圖
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
- **重複執行不重複插入**：寫入前先清空或用 `if_exists='replace'`／唯一鍵避免重複。
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

## 十、部署：上傳 GitHub（步驟 21）

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
- 建議加上 `.gitignore`（排除 `data.db`、`.env`、API Key）。
- 可進一步部署到 Streamlit Community Cloud（免費）對外分享。

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

### A.2 用玻璃卡片包住每個區塊

```python
st.markdown('<div class="glass-header"><h1>Taiwan Weather Forecast</h1></div>',
            unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    selected = st.selectbox('選擇地區', regions)
    st.markdown('</div>', unsafe_allow_html=True)
```

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
