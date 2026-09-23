"""示範資料（DEMO ONLY）。

⚠️ 這是人工編造的示範資料，**不是**中央氣象署的即時預報，僅供在沒有授權碼
或無法連網時驗證 UI 與資料流。畫面上會標示為「示範資料」。

結構刻意模擬真實 F-D0047-091 的新版大寫格式，讓 fetcher.parse 能直接處理，
同時涵蓋測試情境：同日多時段、缺值（'-'）。
"""
from __future__ import annotations

from backend.fetcher import parse, ParseResult

# 以「今天」為基準日，往後排幾天，避免示範資料看起來過期
from datetime import datetime, timedelta, timezone

_TZ = timezone(timedelta(hours=8))


def _day(offset: int) -> str:
    return (datetime.now(_TZ) + timedelta(days=offset)).strftime("%Y-%m-%d")


def _time_block(day: str, half: str, maxt, mint, pop):
    """建立一個 12 小時時段（half='am' 06-18, 'pm' 18-翌日06）。"""
    if half == "am":
        start, end = f"{day}T06:00:00+08:00", f"{day}T18:00:00+08:00"
    else:
        start, end = f"{day}T18:00:00+08:00", f"{day}T18:00:00+08:00"
    return start, end, maxt, mint, pop


def _location(name, geocode, lat, lng, blocks):
    """blocks: list of (start,end,maxt,mint,pop) 字串或 '-'。"""
    def elem(elname, valkey, idx):
        return {
            "ElementName": elname,
            "Time": [
                {"StartTime": b[0], "EndTime": b[1],
                 "ElementValue": [{valkey: str(b[idx])}]}
                for b in blocks
            ],
        }
    return {
        "LocationName": name,
        "Geocode": geocode,
        "Latitude": str(lat),
        "Longitude": str(lng),
        "WeatherElement": [
            elem("最高溫度", "MaxTemperature", 2),
            elem("最低溫度", "MinTemperature", 3),
            elem("12小時降雨機率", "ProbabilityOfPrecipitation", 4),
        ],
    }


def demo_raw() -> dict:
    """回傳模擬 CWA 回應的 dict（DEMO）。"""
    d0, d1, d2 = _day(0), _day(1), _day(2)

    taipei_blocks = [
        _time_block(d0, "am", 30, 26, 20),
        _time_block(d0, "pm", 28, 25, 60),   # 同一天多時段：pm 降雨 60%
        _time_block(d1, "am", 31, 27, 10),
        _time_block(d1, "pm", 29, 26, 80),   # 隔天高降雨 → 觸發帶傘
        _time_block(d2, "am", 32, 28, "-"),  # 缺值示範
    ]
    kaohsiung_blocks = [
        _time_block(d0, "am", 33, 27, 10),
        _time_block(d0, "pm", 31, 26, 20),
        _time_block(d1, "am", 34, 28, 0),
        _time_block(d1, "pm", 32, 27, 10),
        _time_block(d2, "am", 33, 28, 30),
    ]

    return {
        "success": "true",
        "records": {
            "Locations": [{
                "LocationsName": "台灣",
                "DatasetDescription": "（示範資料）臺灣各縣市未來逐12小時天氣預報",
                "Location": [
                    _location("臺北市", "63000000", 25.0330, 121.5654, taipei_blocks),
                    _location("高雄市", "64000000", 22.6273, 120.3014, kaohsiung_blocks),
                ],
            }],
        },
    }


def demo_parse_result() -> ParseResult:
    """回傳解析後的 ParseResult（DEMO）。"""
    return parse(demo_raw())
