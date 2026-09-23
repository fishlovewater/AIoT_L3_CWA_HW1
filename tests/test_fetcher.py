"""fetcher 解析行為測試（用固定範例，驗證行為而非複製實作）。"""
from __future__ import annotations

import pytest

from backend import fetcher


def _loc(name, geocode, lat, lng, times_max, times_min, times_pop):
    """建一個縣市 location（新版大寫結構）。times_* 為 [(start,end,value)]。"""
    def elem(elname, valkey, times):
        return {
            "ElementName": elname,
            "Time": [
                {"StartTime": s, "EndTime": e,
                 "ElementValue": [{valkey: str(v)}]}
                for (s, e, v) in times
            ],
        }
    return {
        "LocationName": name, "Geocode": geocode,
        "Latitude": str(lat), "Longitude": str(lng),
        "WeatherElement": [
            elem("最高溫度", "MaxTemperature", times_max),
            elem("最低溫度", "MinTemperature", times_min),
            elem("12小時降雨機率", "ProbabilityOfPrecipitation", times_pop),
        ],
    }


def _wrap(*locations):
    return {"success": "true",
            "records": {"Locations": [{"LocationsName": "台灣",
                                       "Location": list(locations)}]}}


def test_parse_basic_pairs_by_time_key():
    """同一時間鍵的 MaxT/MinT/PoP 要配在同一列。"""
    s1 = ("2026-09-23T06:00:00+08:00", "2026-09-23T18:00:00+08:00")
    data = _wrap(_loc("臺北市", "63000000", 25.0, 121.5,
                      [(*s1, 30)], [(*s1, 25)], [(*s1, 40)]))
    res = fetcher.parse(data)
    assert len(res.records) == 1
    r = res.records[0]
    assert r["maxT"] == 30 and r["minT"] == 25 and r["pop"] == 40
    assert r["geocode"] == "63000000"
    assert r["lat"] == 25.0 and r["lng"] == 121.5


def test_parse_same_day_multiple_segments_not_collapsed():
    """同一天多個 12 小時時段要各自成列，不被壓成一筆。"""
    am = ("2026-09-23T06:00:00+08:00", "2026-09-23T18:00:00+08:00")
    pm = ("2026-09-23T18:00:00+08:00", "2026-09-24T06:00:00+08:00")
    data = _wrap(_loc("臺北市", "63000000", 25.0, 121.5,
                      [(*am, 30), (*pm, 28)],
                      [(*am, 25), (*pm, 24)],
                      [(*am, 20), (*pm, 60)]))
    res = fetcher.parse(data)
    assert len(res.records) == 2
    starts = {r["startTime"] for r in res.records}
    assert am[0] in starts and pm[0] in starts


def test_parse_missing_value_becomes_none_not_zero():
    """缺值 '-' 要轉成 None，不能當 0。"""
    s1 = ("2026-09-23T06:00:00+08:00", "2026-09-23T18:00:00+08:00")
    data = _wrap(_loc("臺北市", "63000000", 25.0, 121.5,
                      [(*s1, 30)], [(*s1, "-")], [(*s1, "-")]))
    res = fetcher.parse(data)
    r = res.records[0]
    assert r["maxT"] == 30
    assert r["minT"] is None
    assert r["pop"] is None


def test_parse_cross_county_same_geocode_distinct():
    """不同縣市（不同 geocode）不可混淆。"""
    s1 = ("2026-09-23T06:00:00+08:00", "2026-09-23T18:00:00+08:00")
    data = _wrap(
        _loc("臺北市", "63000000", 25.0, 121.5, [(*s1, 30)], [(*s1, 25)], [(*s1, 10)]),
        _loc("高雄市", "64000000", 22.6, 120.3, [(*s1, 33)], [(*s1, 27)], [(*s1, 10)]),
    )
    res = fetcher.parse(data)
    geocodes = {r["geocode"] for r in res.records}
    assert geocodes == {"63000000", "64000000"}


def test_parse_malformed_location_skipped_not_crash():
    """單一 location 結構異常只略過並計數，不影響其他。"""
    s1 = ("2026-09-23T06:00:00+08:00", "2026-09-23T18:00:00+08:00")
    good = _loc("臺北市", "63000000", 25.0, 121.5, [(*s1, 30)], [(*s1, 25)], [(*s1, 10)])
    bad = {"LocationName": "壞資料", "WeatherElement": "not-a-list"}
    data = _wrap(good, bad)
    res = fetcher.parse(data)
    assert len(res.records) == 1
    assert res.skipped == 1


def test_validate_rejects_empty():
    """空解析結果要被拒絕，避免以空資料覆寫。"""
    with pytest.raises(fetcher.FetchError):
        fetcher.validate(fetcher.ParseResult())


def test_validate_rejects_all_missing_temp():
    s1 = ("2026-09-23T06:00:00+08:00", "2026-09-23T18:00:00+08:00")
    data = _wrap(_loc("臺北市", "63000000", 25.0, 121.5,
                      [(*s1, "-")], [(*s1, "-")], [(*s1, 30)]))
    res = fetcher.parse(data)
    with pytest.raises(fetcher.FetchError):
        fetcher.validate(res)


def test_real_sample_structure_if_present():
    """若有真實 API 樣本，確認能解析出多個縣市與溫度。"""
    import os
    import json
    path = os.path.join(os.path.dirname(__file__), "fixtures",
                        "real_sample_structure.json")
    if not os.path.exists(path):
        pytest.skip("無真實樣本檔")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    res = fetcher.parse(data)
    fetcher.validate(res)  # 不應丟例外
    counties = {r["county"] for r in res.records}
    assert len(counties) >= 10  # 應有約 22 縣市
