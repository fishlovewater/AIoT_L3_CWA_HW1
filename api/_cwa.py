"""api/_cwa.py — Vercel serverless 用的輕量 CWA 存取層。

與 backend/fetcher.py 相同的解析與每日彙整邏輯，但**不依賴 pandas / streamlit**，
只用標準庫 + requests，讓 Vercel 函式體積小、冷啟動快。

Vercel 是無伺服器環境：沒有持久磁碟，不能存 SQLite。因此這裡每次請求直接
呼叫 CWA API，並用「行程內短期快取」降低重複請求（同一函式實例存活期間有效）。
授權碼從環境變數 CWA_API_KEY 取得（在 Vercel 專案 Settings -> Environment Variables 設定）。
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional

import requests

CWA_BASE = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
DATASET_ID = "F-D0047-091"
DEFAULT_TIMEOUT = 20
CACHE_TTL_SECONDS = 30 * 60  # 30 分鐘，配合 CWA 更新頻率

MIN_T_NAMES = {"最低溫度", "MinT"}
MAX_T_NAMES = {"最高溫度", "MaxT"}
POP_NAMES = {"12小時降雨機率", "PoP12h", "PoP"}
_VALUE_KEYS = ("MaxTemperature", "MinTemperature", "Temperature",
               "ProbabilityOfPrecipitation", "value")

# 行程內快取：{ "raw": (timestamp, data) }
_cache: dict[str, tuple[float, Any]] = {}


class CwaError(Exception):
    """CWA 取得或解析失敗（訊息不含授權碼）。"""


def get_api_key() -> str:
    key = (os.environ.get("CWA_API_KEY") or "").strip()
    if not key:
        raise CwaError("找不到 CWA_API_KEY 環境變數。請在 Vercel 專案設定中加入。")
    return key


def _fetch_raw() -> dict:
    now = time.time()
    cached = _cache.get("raw")
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    url = f"{CWA_BASE}/{DATASET_ID}"
    try:
        resp = requests.get(url, params={"Authorization": get_api_key(),
                                         "format": "JSON"}, timeout=DEFAULT_TIMEOUT)
    except requests.Timeout as exc:
        raise CwaError("呼叫 CWA API 逾時。") from exc
    except requests.RequestException as exc:
        raise CwaError(f"呼叫 CWA API 網路錯誤：{type(exc).__name__}") from exc

    if resp.status_code == 401:
        raise CwaError("CWA API 回應 401：授權碼無效。")
    if resp.status_code != 200:
        raise CwaError(f"CWA API 回應 HTTP {resp.status_code}")
    try:
        data = resp.json()
    except ValueError as exc:
        raise CwaError("CWA API 回應非合法 JSON。") from exc

    _cache["raw"] = (now, data)
    return data


# ---- 解析（與 backend/fetcher.py 一致的規則）----
def _get(d: dict, *names: str) -> Any:
    for n in names:
        if isinstance(d, dict) and n in d:
            return d[n]
    return None


def _looks_number(v: Any) -> bool:
    try:
        float(str(v))
        return True
    except (TypeError, ValueError):
        return False


def _to_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    s = str(v).strip()
    if s in ("", "-", "X", "x", "None", "null"):
        return None
    try:
        return int(round(float(s)))
    except (TypeError, ValueError):
        return None


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip()
    if s in ("", "-", "None", "null"):
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _element_value(time_entry: dict) -> Optional[str]:
    ev = _get(time_entry, "ElementValue", "elementValue")
    if not isinstance(ev, list) or not ev:
        return None
    first = ev[0]
    if not isinstance(first, dict) or not first:
        return None
    for k in _VALUE_KEYS:
        if k in first:
            return str(first[k])
    for v in first.values():
        if _looks_number(v):
            return str(v)
    vals = list(first.values())
    return str(vals[0]) if vals else None


def _index_by_time(element: Optional[dict]) -> dict[tuple, Optional[str]]:
    out: dict[tuple, Optional[str]] = {}
    if not element:
        return out
    times = _get(element, "Time", "time")
    if not isinstance(times, list):
        return out
    for t in times:
        if not isinstance(t, dict):
            continue
        start = _get(t, "StartTime", "startTime", "DataTime", "dataTime")
        end = _get(t, "EndTime", "endTime") or start
        if start is None:
            continue
        out[(str(start), str(end))] = _element_value(t)
    return out


def _pick(by_name: dict[str, dict], candidates: set[str]) -> Optional[dict]:
    lower = {k.lower(): v for k, v in by_name.items()}
    for c in candidates:
        if c in by_name:
            return by_name[c]
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def parse_segments(data: dict) -> list[dict]:
    """回傳原始 12 小時時段列（每縣市多筆）。"""
    records: list[dict] = []
    records_root = _get(data, "records", "Records") or {}
    outer = _get(records_root, "Locations", "locations")
    locations = []
    if isinstance(outer, list):
        for item in outer:
            inner = _get(item, "Location", "location")
            if isinstance(inner, list):
                locations.extend(inner)
    if not locations:
        inner = _get(records_root, "Location", "location")
        if isinstance(inner, list):
            locations = inner

    for loc in locations:
        try:
            name = _get(loc, "LocationName", "locationName")
            geocode = _get(loc, "Geocode", "geocode")
            lat = _to_float(_get(loc, "Latitude", "latitude"))
            lng = _to_float(_get(loc, "Longitude", "longitude"))
            elements = _get(loc, "WeatherElement", "weatherElement")
            if name is None or not isinstance(elements, list):
                continue
            by_name = {str(_get(e, "ElementName", "elementName")): e
                       for e in elements if isinstance(e, dict)}
            min_idx = _index_by_time(_pick(by_name, MIN_T_NAMES))
            max_idx = _index_by_time(_pick(by_name, MAX_T_NAMES))
            pop_idx = _index_by_time(_pick(by_name, POP_NAMES))
            keys = set(min_idx) | set(max_idx) | set(pop_idx)
            for key in sorted(keys):
                start, end = key
                records.append({
                    "geocode": str(geocode) if geocode is not None else None,
                    "county": str(name),
                    "lat": lat, "lng": lng,
                    "startTime": start, "endTime": end,
                    "minT": _to_int(min_idx.get(key)),
                    "maxT": _to_int(max_idx.get(key)),
                    "pop": _to_int(pop_idx.get(key)),
                })
        except Exception:
            continue
    return records


def aggregate_daily(segments: list[dict]) -> dict[str, list[dict]]:
    """依 geocode 分組，回傳 { geocode: [ {day, dayMinT, dayMaxT, dayPop}, ... ] }。"""
    by_geo: dict[str, dict] = {}
    for r in segments:
        geo = r["geocode"] or f'{r["county"]}'
        day = r["startTime"][:10]
        g = by_geo.setdefault(geo, {
            "geocode": geo, "county": r["county"],
            "lat": r["lat"], "lng": r["lng"], "days": {},
        })
        d = g["days"].setdefault(day, {"mins": [], "maxs": [], "pops": []})
        if r["minT"] is not None:
            d["mins"].append(r["minT"])
        if r["maxT"] is not None:
            d["maxs"].append(r["maxT"])
        if r["pop"] is not None:
            d["pops"].append(r["pop"])
    out: dict[str, list[dict]] = {}
    for geo, g in by_geo.items():
        rows = []
        for day in sorted(g["days"]):
            d = g["days"][day]
            rows.append({
                "day": day,
                "dayMinT": min(d["mins"]) if d["mins"] else None,
                "dayMaxT": max(d["maxs"]) if d["maxs"] else None,
                "dayPop": max(d["pops"]) if d["pops"] else None,
            })
        out[geo] = rows
    return out


def build_payload() -> dict:
    """組出前端要的完整資料：地區清單 + 每地區每日 + 座標。"""
    data = _fetch_raw()
    segments = parse_segments(data)
    if not segments:
        raise CwaError("解析結果為空。")
    daily = aggregate_daily(segments)

    # 地區 meta（含座標）
    meta: dict[str, dict] = {}
    for r in segments:
        geo = r["geocode"] or r["county"]
        meta.setdefault(geo, {"geocode": geo, "county": r["county"],
                              "lat": r["lat"], "lng": r["lng"]})

    regions = [{"geocode": g, "label": m["county"]}
               for g, m in sorted(meta.items(), key=lambda kv: kv[1]["county"])]

    # 可用日期（所有地區日期聯集）
    days = sorted({row["day"] for rows in daily.values() for row in rows})

    return {
        "success": True,
        "regions": regions,
        "meta": meta,
        "daily": daily,
        "days": days,
        "source": "中央氣象署開放資料 F-D0047-091（逐12小時，彙整為每日）",
    }
