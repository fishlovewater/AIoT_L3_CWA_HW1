"""backend/database.py — SQLite 存取層。

職責：
- 建立資料表（保留原始 12 小時時段，唯一鍵 (geocode, startTime, endTime)）。
- 參數化查詢（避免 SQL injection）。
- upsert：重複抓取更新預報，但不新增重複列。
- 儲存抓取時間 fetchedAt 供畫面顯示「資料最後更新時間」。

資料庫位置可由環境變數 WEATHER_DB_PATH 設定，避免依賴目前工作目錄；
預設放在本套件所在專案根目錄的 data.db。
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

# 專案根目錄（backend/ 的上一層）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def db_path() -> str:
    """回傳資料庫檔案路徑；可用環境變數 WEATHER_DB_PATH 覆寫。"""
    env = os.environ.get("WEATHER_DB_PATH")
    if env:
        return env
    return str(_PROJECT_ROOT / "data.db")


@contextmanager
def get_conn(path: Optional[str] = None):
    """取得連線的 context manager，結束時自動 commit/close。"""
    conn = sqlite3.connect(path or db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path: Optional[str] = None) -> None:
    """建立資料表（若不存在）。"""
    with get_conn(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS TemperatureForecasts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                geocode   TEXT,
                county    TEXT,
                town      TEXT,
                lat       REAL,          -- 來源提供的緯度
                lng       REAL,          -- 來源提供的經度
                startTime TEXT NOT NULL,
                endTime   TEXT NOT NULL,
                minT      REAL,          -- 可為 NULL（缺值）
                maxT      REAL,          -- 可為 NULL（缺值）
                pop       REAL,          -- 降雨機率(%)，可為 NULL（缺值）
                fetchedAt TEXT NOT NULL, -- ISO8601 抓取時間
                UNIQUE (geocode, startTime, endTime)
            )
            """
        )
        # 加速常用查詢
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_forecast_geocode "
            "ON TemperatureForecasts (geocode, startTime)"
        )


def _valid_key(rec: dict) -> bool:
    """upsert 需要唯一鍵三欄齊全；geocode 缺失時退回用 county+town 當識別。"""
    if not rec.get("startTime") or not rec.get("endTime"):
        return False
    if rec.get("geocode"):
        return True
    # 沒有 geocode 就用 county|town 合成一個穩定識別，避免同名鄉鎮混淆
    return bool(rec.get("town"))


def _ensure_geocode(rec: dict) -> dict:
    """若無 geocode，用 'county|town' 合成識別，確保唯一鍵穩定且不同縣市不混淆。"""
    rec = dict(rec)
    if not rec.get("geocode"):
        county = rec.get("county") or "?"
        town = rec.get("town") or "?"
        rec["geocode"] = f"{county}|{town}"
    return rec


def save(records: Iterable[dict], fetched_at: str,
         path: Optional[str] = None) -> int:
    """upsert 一批資料。回傳實際寫入（新增或更新）的列數。
    同 (geocode, startTime, endTime) 會更新而非重複新增。"""
    rows = []
    for r in records:
        if not _valid_key(r):
            continue
        r = _ensure_geocode(r)
        rows.append({
            "geocode": r["geocode"],
            "county": r.get("county"),
            "town": r.get("town"),
            "lat": r.get("lat"),
            "lng": r.get("lng"),
            "startTime": r["startTime"],
            "endTime": r["endTime"],
            "minT": r.get("minT"),
            "maxT": r.get("maxT"),
            "pop": r.get("pop"),
            "fetchedAt": fetched_at,
        })
    if not rows:
        return 0
    with get_conn(path) as conn:
        conn.executemany(
            """
            INSERT INTO TemperatureForecasts
                (geocode, county, town, lat, lng,
                 startTime, endTime, minT, maxT, pop, fetchedAt)
            VALUES
                (:geocode, :county, :town, :lat, :lng,
                 :startTime, :endTime, :minT, :maxT, :pop, :fetchedAt)
            ON CONFLICT (geocode, startTime, endTime) DO UPDATE SET
                county    = excluded.county,
                town      = excluded.town,
                lat       = excluded.lat,
                lng       = excluded.lng,
                minT      = excluded.minT,
                maxT      = excluded.maxT,
                pop       = excluded.pop,
                fetchedAt = excluded.fetchedAt
            """,
            rows,
        )
    return len(rows)


def query_df(sql: str, params: tuple = (), path: Optional[str] = None) -> pd.DataFrame:
    """執行參數化查詢，回傳 DataFrame。"""
    with get_conn(path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def last_fetched_at(path: Optional[str] = None) -> Optional[str]:
    """回傳資料庫中最新的抓取時間；空表回傳 None。"""
    with get_conn(path) as conn:
        row = conn.execute(
            "SELECT MAX(fetchedAt) AS m FROM TemperatureForecasts"
        ).fetchone()
    return row["m"] if row and row["m"] else None


def row_count(path: Optional[str] = None) -> int:
    """回傳資料列數（供測試/診斷）。"""
    with get_conn(path) as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM TemperatureForecasts").fetchone()
    return int(row["c"]) if row else 0
