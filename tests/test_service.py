"""tests/test_service.py — 服務層資料查詢與帶傘提醒邏輯測試。"""
from __future__ import annotations

import os
import tempfile
import pandas as pd
import pytest

from backend import database, service


@pytest.fixture
def populated_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        database.init_db(path)
        records = [
            # 臺北市 同日兩時段
            {
                "geocode": "63000000",
                "county": "臺北市",
                "town": "臺北市",
                "lat": 25.033,
                "lng": 121.565,
                "startTime": "2026-09-23T06:00:00+08:00",
                "endTime": "2026-09-23T18:00:00+08:00",
                "minT": 26,
                "maxT": 32,
                "pop": 20,
            },
            {
                "geocode": "63000000",
                "county": "臺北市",
                "town": "臺北市",
                "lat": 25.033,
                "lng": 121.565,
                "startTime": "2026-09-23T18:00:00+08:00",
                "endTime": "2026-09-24T06:00:00+08:00",
                "minT": 24,
                "maxT": 28,
                "pop": 70,  # > 50% 觸發帶傘
            },
            # 臺北市 隔天時段
            {
                "geocode": "63000000",
                "county": "臺北市",
                "town": "臺北市",
                "lat": 25.033,
                "lng": 121.565,
                "startTime": "2026-09-24T06:00:00+08:00",
                "endTime": "2026-09-24T18:00:00+08:00",
                "minT": 23,
                "maxT": 30,
                "pop": 10,
            },
            # 高雄市 同日一時段
            {
                "geocode": "64000000",
                "county": "高雄市",
                "town": "高雄市",
                "lat": 22.627,
                "lng": 120.301,
                "startTime": "2026-09-23T06:00:00+08:00",
                "endTime": "2026-09-23T18:00:00+08:00",
                "minT": 27,
                "maxT": 34,
                "pop": None,  # 缺值
            },
        ]
        database.save(records, "2026-09-23T12:00:00+08:00", path=path)
        yield path
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_list_regions(populated_db):
    regions = service.list_regions(path=populated_db)
    assert len(regions) == 2
    geocodes = {r["geocode"] for r in regions}
    assert geocodes == {"63000000", "64000000"}
    labels = {r["label"] for r in regions}
    assert labels == {"臺北市", "高雄市"}


def test_available_days(populated_db):
    days = service.available_days(path=populated_db)
    assert days == ["2026-09-23", "2026-09-24"]


def test_get_region_daily_aggregation(populated_db):
    daily = service.get_region_daily("63000000", path=populated_db)
    assert len(daily) == 2
    # 2026-09-23：minT = MIN(26, 24) = 24; maxT = MAX(32, 28) = 32; pop = MAX(20, 70) = 70
    d23 = daily[daily["day"] == "2026-09-23"].iloc[0]
    assert d23["dayMinT"] == 24
    assert d23["dayMaxT"] == 32
    assert d23["dayPop"] == 70

    # 2026-09-24
    d24 = daily[daily["day"] == "2026-09-24"].iloc[0]
    assert d24["dayMinT"] == 23
    assert d24["dayMaxT"] == 30
    assert d24["dayPop"] == 10


def test_get_day_all_regions(populated_db):
    map_df = service.get_day_all_regions("2026-09-23", path=populated_db)
    assert len(map_df) == 2
    tpe = map_df[map_df["county"] == "臺北市"].iloc[0]
    assert tpe["dayMaxT"] == 32
    khh = map_df[map_df["county"] == "高雄市"].iloc[0]
    assert khh["dayMaxT"] == 34
    assert pd.isna(khh["dayPop"])


def test_umbrella_alert_triggers_over_threshold(populated_db):
    daily = service.get_region_daily("63000000", path=populated_db)
    alert = service.umbrella_alert(daily, threshold=50)
    assert alert is not None
    assert alert["max_pop"] == 70
    assert "2026-09-23" in alert["days"]


def test_umbrella_alert_not_triggered_under_threshold(populated_db):
    daily = service.get_region_daily("63000000", path=populated_db)
    # 門檻提高到 80，70% 不應觸發
    alert = service.umbrella_alert(daily, threshold=80)
    assert alert is None


def test_umbrella_alert_day_filter(populated_db):
    daily = service.get_region_daily("63000000", path=populated_db)
    # 2026-09-24 pop 為 10%，指定此日不觸發
    alert_d24 = service.umbrella_alert(daily, threshold=50, day="2026-09-24")
    assert alert_d24 is None

    # 2026-09-23 pop 為 70%，指定此日觸發
    alert_d23 = service.umbrella_alert(daily, threshold=50, day="2026-09-23")
    assert alert_d23 is not None
    assert alert_d23["max_pop"] == 70


def test_umbrella_alert_missing_pop_does_not_trigger():
    # 缺值 DataFrame
    df = pd.DataFrame([{"day": "2026-09-23", "dayPop": None}])
    assert service.umbrella_alert(df, threshold=50) is None
