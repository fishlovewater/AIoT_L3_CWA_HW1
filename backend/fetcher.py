"""backend/fetcher.py — 從中央氣象署（CWA）取得並解析一週逐 12 小時預報。

資料集：F-D0047-091「臺灣各縣市鄉鎮未來 1 週逐 12 小時天氣預報」。
原生時間粒度為每 12 小時一段（見 datasetDescription）。

設計重點（對應 workflow.md / 專案指令）：
- 授權碼只從 st.secrets 或環境變數 CWA_API_KEY 取得，絕不寫死、不回傳、不記錄。
- 具 timeout 與 HTTP 錯誤處理。
- 解析採「按時間鍵 (startTime, endTime) 配對」，不用 zip、不用會因單一缺欄
  炸掉整批的 next(...)/int(...)。
- 缺值以 None 保留，不當 0；記錄略過數量以便診斷。
- 解析結果會做基本格式驗證（非空、欄位齊全），驗證失敗回報錯誤。

本檔同時相容 CWA 新版（大寫 Locations/Location/WeatherElement/ElementValue）
與舊版（小寫 locations/location/weatherElement/elementValue）結構，以實際回應為準。
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

log = logging.getLogger(__name__)

CWA_BASE = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
DATASET_ID = "F-D0047-091"  # 一週逐 12 小時
DEFAULT_TIMEOUT = 30

# 溫度與降雨機率在不同版本可能的 element 名稱（大小寫皆容忍）
MIN_T_NAMES = {"MinT", "最低溫度"}
MAX_T_NAMES = {"MaxT", "最高溫度"}
POP_NAMES = {"PoP12h", "PoP", "12小時降雨機率"}


class FetchError(Exception):
    """取得或驗證 CWA 資料失敗。訊息不含授權碼。"""


@dataclass
class ParseResult:
    """解析結果：records 為乾淨資料列；skipped 為略過筆數與原因，便於診斷。"""
    records: list[dict] = field(default_factory=list)
    skipped: int = 0
    notes: list[str] = field(default_factory=list)


def get_api_key() -> str:
    """取得授權碼：優先 st.secrets（雲端），退回環境變數（本機 .env）。
    找不到就丟出清楚的錯誤（不含金鑰內容）。"""
    # st.secrets（僅在 Streamlit 執行環境中可用）
    try:
        import streamlit as st  # noqa: WPS433 (本地 import 避免非 Streamlit 環境負擔)
        try:
            if "CWA_API_KEY" in st.secrets:
                val = str(st.secrets["CWA_API_KEY"]).strip()
                if val:
                    return val
        except Exception:  # st.secrets 未設定時可能丟例外
            pass
    except ImportError:
        pass

    val = (os.environ.get("CWA_API_KEY") or "").strip()
    if val:
        return val

    raise FetchError(
        "找不到 CWA 授權碼。請設定環境變數 CWA_API_KEY（本機可用 .env），"
        "或在 Streamlit Community Cloud 的 Secrets 設定 CWA_API_KEY。"
    )


def fetch_raw(api_key: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """呼叫 CWA API，回傳原始 JSON dict。含 timeout 與 HTTP 錯誤處理。"""
    key = api_key or get_api_key()
    url = f"{CWA_BASE}/{DATASET_ID}"
    try:
        resp = requests.get(
            url,
            params={"Authorization": key, "format": "JSON"},
            timeout=timeout,
        )
    except requests.Timeout as exc:
        raise FetchError(f"呼叫 CWA API 逾時（{timeout}s）。") from exc
    except requests.RequestException as exc:
        # 不把可能含金鑰的 URL/params 放進訊息
        raise FetchError(f"呼叫 CWA API 發生網路錯誤：{type(exc).__name__}") from exc

    if resp.status_code == 401:
        raise FetchError("CWA API 回應 401：授權碼無效或未帶授權碼。")
    if resp.status_code != 200:
        raise FetchError(f"CWA API 回應非 200：HTTP {resp.status_code}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise FetchError("CWA API 回應非合法 JSON。") from exc

    if not isinstance(data, dict) or not data.get("success") in (True, "true", None):
        # 某些錯誤情況 success 會是 "false"
        if isinstance(data, dict) and str(data.get("success")).lower() == "false":
            raise FetchError("CWA API 回應 success=false（可能授權碼錯誤或參數有誤）。")
    return data


# ---------------------------------------------------------------------------
# 解析：相容大小寫兩種結構
# ---------------------------------------------------------------------------
def _get(d: dict, *names: str) -> Any:
    """從 dict 取第一個存在的鍵（相容大小寫命名）。"""
    for n in names:
        if n in d:
            return d[n]
    return None


def _locations_container(data: dict) -> list[dict]:
    """取得 location 清單。相容：
    新版：records.Locations[0].Location[]
    舊版：records.locations[0].location[]
    也容忍 records.location[]（無外層 Locations）。"""
    records = _get(data, "records", "Records") or {}
    # 外層 Locations / locations
    outer = _get(records, "Locations", "locations")
    if isinstance(outer, list) and outer:
        first = outer[0] or {}
        inner = _get(first, "Location", "location")
        county = _get(first, "LocationsName", "locationsName", "DatasetDescription")
        if isinstance(inner, list):
            return [_with_parent(loc, county) for loc in inner]
    # 無外層，直接 location
    inner = _get(records, "Location", "location")
    if isinstance(inner, list):
        return [_with_parent(loc, None) for loc in inner]
    return []


def _with_parent(loc: dict, county: Optional[str]) -> dict:
    """把縣市名塞進 location 方便後續使用（不覆蓋既有欄位）。"""
    loc = dict(loc)
    loc.setdefault("_parentCounty", county)
    return loc


def _element_value(time_entry: dict, prefer_numeric: bool = True) -> Optional[str]:
    """從一個 Time 條目取出數值字串。相容 ElementValue/elementValue 結構：
    - 新版：[{"MinT": "20"}] 或 [{"value": "20", "measures": "..."}]
    - 舊版：[{"value": "20"}]
    回傳字串或 None。"""
    ev = _get(time_entry, "ElementValue", "elementValue")
    if not isinstance(ev, list) or not ev:
        return None
    first = ev[0]
    if not isinstance(first, dict) or not first:
        return None
    # 優先找看起來像數值的欄位
    # 常見鍵："value"、"MinT"、"MaxT"、"ProbabilityOfPrecipitation"、"Temperature"
    candidates = list(first.values())
    if prefer_numeric:
        for v in candidates:
            if _looks_number(v):
                return str(v)
    # 退回第一個值
    return str(candidates[0]) if candidates else None


def _looks_number(v: Any) -> bool:
    try:
        float(str(v))
        return True
    except (TypeError, ValueError):
        return False


def _to_int(v: Any) -> Optional[int]:
    """轉整數；空值、'-'、非數字都回 None（不當 0）。"""
    if v is None:
        return None
    s = str(v).strip()
    if s in ("", "-", "X", "x", "None", "null"):
        return None
    try:
        return int(round(float(s)))
    except (TypeError, ValueError):
        return None


def _index_element_by_time(element: Optional[dict]) -> dict[tuple, Optional[str]]:
    """把一個 weatherElement 的 Time[] 轉成 {(startTime, endTime): value_str}。
    相容 startTime/endTime 與 dataTime（瞬時值）。"""
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


def parse(data: dict) -> ParseResult:
    """解析 CWA 一週逐 12 小時預報。

    回傳 ParseResult：records 每列為
      {geocode, county, town, startTime, endTime, minT, maxT, pop}
    - 按 (startTime, endTime) 時間鍵配對 MinT/MaxT/PoP，不用 zip。
    - 任一元素缺該時段值 -> 該欄位 None（缺值保留）。
    - 單一 location 結構異常只略過該筆並計數，不影響其他資料。
    """
    result = ParseResult()
    locations = _locations_container(data)
    if not locations:
        result.notes.append("找不到 location 清單（結構可能與預期不同）。")
        return result

    for loc in locations:
        try:
            town = _get(loc, "LocationName", "locationName")
            geocode = _get(loc, "Geocode", "geocode")
            county = loc.get("_parentCounty")
            elements = _get(loc, "WeatherElement", "weatherElement")
            if town is None or not isinstance(elements, list):
                result.skipped += 1
                continue

            # 依名稱歸類 element（相容大小寫/中英名稱）
            by_name: dict[str, dict] = {}
            for el in elements:
                if not isinstance(el, dict):
                    continue
                name = _get(el, "ElementName", "elementName")
                if name is not None:
                    by_name[str(name)] = el

            min_el = _pick(by_name, MIN_T_NAMES)
            max_el = _pick(by_name, MAX_T_NAMES)
            pop_el = _pick(by_name, POP_NAMES)

            min_idx = _index_element_by_time(min_el)
            max_idx = _index_element_by_time(max_el)
            pop_idx = _index_element_by_time(pop_el)

            keys = set(min_idx) | set(max_idx) | set(pop_idx)
            if not keys:
                result.skipped += 1
                continue

            for key in sorted(keys):
                start, end = key
                result.records.append({
                    "geocode": str(geocode) if geocode is not None else None,
                    "county": str(county) if county is not None else None,
                    "town": str(town),
                    "startTime": start,
                    "endTime": end,
                    "minT": _to_int(min_idx.get(key)),
                    "maxT": _to_int(max_idx.get(key)),
                    "pop": _to_int(pop_idx.get(key)),
                })
        except Exception as exc:  # 單筆異常不影響整批
            result.skipped += 1
            log.warning("解析某 location 時略過：%s", type(exc).__name__)
            continue

    if result.skipped:
        result.notes.append(f"略過 {result.skipped} 筆結構異常的 location。")
    return result


def _pick(by_name: dict[str, dict], candidates: set[str]) -> Optional[dict]:
    """從 element 名稱表挑出第一個符合的（大小寫不敏感）。"""
    lower = {k.lower(): v for k, v in by_name.items()}
    for c in candidates:
        if c in by_name:
            return by_name[c]
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def validate(result: ParseResult) -> None:
    """基本檢查：非空、欄位齊全、至少有部分溫度數值。不通過丟 FetchError。"""
    if not result.records:
        raise FetchError("解析結果為空，拒絕以空資料覆寫現有預報。")
    required = {"geocode", "county", "town", "startTime", "endTime", "minT", "maxT", "pop"}
    sample = result.records[0]
    missing = required - set(sample.keys())
    if missing:
        raise FetchError(f"解析結果缺少必要欄位：{sorted(missing)}")
    has_temp = any(r["minT"] is not None or r["maxT"] is not None for r in result.records)
    if not has_temp:
        raise FetchError("解析結果所有時段皆無溫度數值，資料可能異常。")


def fetch_and_parse(api_key: Optional[str] = None,
                    timeout: int = DEFAULT_TIMEOUT) -> ParseResult:
    """一次完成：抓取 -> 解析 -> 驗證。回傳通過驗證的 ParseResult。"""
    data = fetch_raw(api_key=api_key, timeout=timeout)
    result = parse(data)
    validate(result)
    return result
