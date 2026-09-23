# 資料定義與 schema 決策（實作前先驗證的結論）

本檔記錄以**實際呼叫 CWA API（F-D0047-091，HTTP 200）**核對後的結論，作為程式實作依據。
驗證方式：以授權碼呼叫一次 API，保存回應結構（不含授權碼）到 `tests/fixtures/`，逐項核對。

## 1. 資料集與涵蓋範圍

- 資料集：`F-D0047-091`，`DatasetDescription = 臺灣各縣市鄉鎮未來1週逐12小時天氣預報`。
- **實際 `Location` 為「22 個縣市」層級**（例：連江縣、臺北市…），**非鄉鎮**。
  - 因此本專案的「地區」= 縣市。原規格提到的「縣市 + 鄉鎮」在此資料集不適用；
    我們以 `county`（縣市）為地區，`town` 欄位存同值（或縣市名）以保持 schema 一致。
  - 若日後改用真正含鄉鎮的資料集（如 F-D0047-089），解析層可沿用，只是 Location 會更細。
- 時間粒度：**每 12 小時一段**，每個縣市 14 段（約 7 天）。
- 時區：`StartTime` 形如 `2026-09-23T06:00:00+08:00`（台灣當地時間 +08:00）。

## 2. JSON 結構（新版大寫）

```
records.Locations[0].Location[]        # 22 縣市
  ├─ LocationName        例 "臺北市"
  ├─ Geocode             8 碼，例 "09007000"、"63000000"
  ├─ Latitude / Longitude   來源直接提供經緯度（地圖優先採用）
  └─ WeatherElement[]
       ├─ ElementName = "最高溫度"  → Time[].ElementValue[0]["MaxTemperature"]
       ├─ ElementName = "最低溫度"  → Time[].ElementValue[0]["MinTemperature"]
       └─ ElementName = "12小時降雨機率" → Time[].ElementValue[0]["ProbabilityOfPrecipitation"]
       Time[]: { StartTime, EndTime, ElementValue:[{...}] }
```

其他可用 element（本專案未全用）：平均溫度、露點、相對濕度、體感溫度、舒適度、
風速、風向、天氣現象、紫外線指數、天氣預報綜合描述。

## 3. 缺值表示

- 缺值以字串 `"-"` 表示（已在實際回應中出現於降雨機率）。
- 解析時 `"-"`、空字串、非數字一律轉為 `None`（不當 0）。

## 4. 時段 vs 每日彙整

- **資料庫保留原始 12 小時時段**，唯一鍵 `(geocode, startTime, endTime)`，重抓只更新不重複。
- **畫面（折線圖、日期地圖）以「每日」呈現**：依同一 `geocode` 與台灣當地日期
  （`substr(startTime,1,10)`，因時間已含 +08:00，直接取日期即當地日）彙整：
  - 每日最低溫 = `MIN(minT)`；每日最高溫 = `MAX(maxT)`。
  - 每日降雨機率 = `MAX(pop)`（保守取當日最高，利於帶傘提醒）。
- 不使用 `zip` 配對不同 element；改以 `(StartTime, EndTime)` 時間鍵配對，避免錯位。
- 不使用 `startTime[:10]` 當唯一鍵，避免同日多時段互相覆蓋。

## 5. 地區識別與座標

- 以 `Geocode`（縣市 8 碼）識別；不同縣市不會混淆。
- 地圖座標**優先使用來源提供的 `Latitude`/`Longitude`**；`data/geo.py` 僅作為
  來源無座標時的備援對照表。

## 6. 地圖溫度指標與圖例

- 地圖顏色代表「該縣市**當日最高溫（dayMaxT）**」，並在畫面附圖例說明。
  - < 20°C 藍、20–25°C 綠、25–30°C 橙、> 30°C 紅。

## 7. 帶傘提醒

- 規則：所選地區（可再限定所選日期）**任一日的每日降雨機率 > 50%** 就提醒帶傘。
- 缺值（NaN）不觸發、不當 0。
