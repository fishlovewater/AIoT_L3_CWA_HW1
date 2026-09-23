"""backend/service.py — UI 查資料的單一入口。

前端（app.py / components.py）只透過本模組取得資料，不直接寫 SQL。

產品定義（對應專案指令）：
- 圖表與日期地圖以「每日」為單位：先保留原始 12 小時時段，再依
  同一行政區與台灣當地日期彙整每日最低溫(MIN(minT))與最高溫(MAX(maxT))。
- 降雨機率同樣以每日彙整取當日最大值（較保守，利於帶傘提醒）。
- 地區以 geocode 識別；同名鄉鎮不混淆。
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from . import database as db


def list_regions(path: Optional[str] = None) -> list[dict]:
    """回傳地區清單：[{'label': '臺北市 中正區', 'geocode': '6300100'}, ...]
    用縣市+鄉鎮顯示、geocode 識別，避免同名鄉鎮混淆。"""
    df = db.query_df(
        "SELECT DISTINCT geocode, county, town FROM TemperatureForecasts "
        "ORDER BY county, town",
        path=path,
    )
    regions = []
    for r in df.itertuples(index=False):
        county = r.county or ""
        town = r.town or ""
        if county and town and county == town:
            label = county
        else:
            label = f"{county} {town}".strip() or (r.geocode or "未知地區")
        regions.append({"label": label, "geocode": r.geocode})
    return regions


def get_region_daily(geocode: str, path: Optional[str] = None) -> pd.DataFrame:
    """某地區的『每日』高低溫與降雨機率（由 12 小時時段彙整）。
    欄位：day, dayMinT, dayMaxT, dayPop。
    彙整時忽略 NULL；某日若完全無值則該欄為 NaN。"""
    return db.query_df(
        """
        SELECT
            substr(startTime, 1, 10) AS day,
            MIN(minT) AS dayMinT,
            MAX(maxT) AS dayMaxT,
            MAX(pop)  AS dayPop
        FROM TemperatureForecasts
        WHERE geocode = ?
        GROUP BY day
        ORDER BY day
        """,
        (geocode,),
        path=path,
    )


def get_region_segments(geocode: str, path: Optional[str] = None) -> pd.DataFrame:
    """某地區的原始 12 小時時段資料（供資料表與診斷）。
    欄位：startTime, endTime, minT, maxT, pop。"""
    return db.query_df(
        "SELECT startTime, endTime, minT, maxT, pop "
        "FROM TemperatureForecasts WHERE geocode = ? ORDER BY startTime",
        (geocode,),
        path=path,
    )


def available_days(path: Optional[str] = None) -> list[str]:
    """資料庫實際有資料的日期清單（給日期選單，避免選到沒資料的日期）。"""
    df = db.query_df(
        "SELECT DISTINCT substr(startTime, 1, 10) AS day "
        "FROM TemperatureForecasts ORDER BY day",
        path=path,
    )
    return df["day"].dropna().tolist()


def get_day_all_regions(day: str, path: Optional[str] = None) -> pd.DataFrame:
    """某一天所有地區的每日高低溫彙整（供地圖）。
    欄位：geocode, county, town, dayMinT, dayMaxT, dayPop。"""
    return db.query_df(
        """
        SELECT
            geocode, county, town, lat, lng,
            MIN(minT) AS dayMinT,
            MAX(maxT) AS dayMaxT,
            MAX(pop)  AS dayPop
        FROM TemperatureForecasts
        WHERE substr(startTime, 1, 10) = ?
        GROUP BY geocode, county, town, lat, lng
        ORDER BY county, town
        """,
        (str(day),),
        path=path,
    )


def last_updated(path: Optional[str] = None) -> Optional[str]:
    """資料最後抓取時間（ISO8601 字串）。"""
    return db.last_fetched_at(path=path)


def umbrella_alert(daily_df: pd.DataFrame, threshold: int = 50,
                   day: Optional[str] = None) -> Optional[dict]:
    """帶傘判斷（純資料邏輯，方便測試）。
    傳入某地區的每日彙整 DataFrame（get_region_daily 的輸出）。
    - day 有值時只看該日；否則看全部日期。
    - 回傳 None 表示不需帶傘；否則回傳 {'max_pop', 'days'}。
    - dayPop 為 NaN（缺值）不觸發、也不當 0。
    """
    if daily_df is None or daily_df.empty or "dayPop" not in daily_df.columns:
        return None
    df = daily_df
    if day is not None:
        df = df[df["day"] == str(day)]
    valid = df[df["dayPop"].notna()]
    if valid.empty:
        return None
    over = valid[valid["dayPop"] > threshold]
    if over.empty:
        return None
    return {
        "max_pop": int(over["dayPop"].max()),
        "days": over["day"].tolist(),
    }
