"""tests/test_database.py — SQLite 資料庫行為測試。"""
from __future__ import annotations

import os
import tempfile
import pytest

from backend import database


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        database.init_db(path)
        yield path
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_init_db_empty_state(temp_db):
    assert database.row_count(temp_db) == 0
    assert database.last_fetched_at(temp_db) is None


def test_save_and_upsert_idempotency(temp_db):
    records = [
        {
            "geocode": "63000000",
            "county": "臺北市",
            "town": "臺北市",
            "lat": 25.033,
            "lng": 121.565,
            "startTime": "2026-09-23T06:00:00+08:00",
            "endTime": "2026-09-23T18:00:00+08:00",
            "minT": 25,
            "maxT": 30,
            "pop": 20,
        }
    ]
    # 第一次寫入
    written1 = database.save(records, "2026-09-23T10:00:00+08:00", path=temp_db)
    assert written1 == 1
    assert database.row_count(temp_db) == 1
    assert database.last_fetched_at(temp_db) == "2026-09-23T10:00:00+08:00"

    # 重複寫入同一時段（更新數值）
    updated_records = [
        {
            "geocode": "63000000",
            "county": "臺北市",
            "town": "臺北市",
            "lat": 25.033,
            "lng": 121.565,
            "startTime": "2026-09-23T06:00:00+08:00",
            "endTime": "2026-09-23T18:00:00+08:00",
            "minT": 24,
            "maxT": 32,
            "pop": 60,
        }
    ]
    written2 = database.save(updated_records, "2026-09-23T11:00:00+08:00", path=temp_db)
    assert written2 == 1
    # 唯一鍵約束生效：筆數維持 1，不產生重複列
    assert database.row_count(temp_db) == 1
    assert database.last_fetched_at(temp_db) == "2026-09-23T11:00:00+08:00"

    df = database.query_df("SELECT * FROM TemperatureForecasts WHERE geocode = ?",
                           ("63000000",), path=temp_db)
    assert len(df) == 1
    assert df.iloc[0]["minT"] == 24
    assert df.iloc[0]["maxT"] == 32
    assert df.iloc[0]["pop"] == 60


def test_missing_values_stored_as_none_not_zero(temp_db):
    records = [
        {
            "geocode": "64000000",
            "county": "高雄市",
            "town": "高雄市",
            "lat": None,
            "lng": None,
            "startTime": "2026-09-23T06:00:00+08:00",
            "endTime": "2026-09-23T18:00:00+08:00",
            "minT": None,
            "maxT": 30,
            "pop": None,
        }
    ]
    database.save(records, "2026-09-23T10:00:00+08:00", path=temp_db)
    df = database.query_df("SELECT * FROM TemperatureForecasts WHERE geocode = ?",
                           ("64000000",), path=temp_db)
    assert len(df) == 1
    row = df.iloc[0]
    import pandas as pd
    assert pd.isna(row["minT"])
    assert row["maxT"] == 30
    assert pd.isna(row["pop"])
