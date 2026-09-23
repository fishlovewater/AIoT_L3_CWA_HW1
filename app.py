"""app.py — 台灣天氣預報 Streamlit 主程式（架構 A：Streamlit 單體 + 分層）。

前端只透過 backend.service 取得資料。UI 採 iOS 液態玻璃風格。
執行：py -3.12 -m streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

# 本機載入 .env；Community Cloud 用 st.secrets，缺 dotenv 也不會壞
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from backend import service
from bootstrap import ensure_fresh_data
from frontend.styles import inject_glass_css
from frontend import components as ui

UMBRELLA_THRESHOLD = 50
DATA_MAX_AGE_HOURS = 6

st.set_page_config(page_title="台灣天氣預報", page_icon="☀️", layout="wide")
inject_glass_css()


# ---- 資料初始化與自動更新（只在每次 session 首次執行時做一次） ----
@st.cache_resource(show_spinner="正在準備天氣資料…")
def _bootstrap_once():
    return ensure_fresh_data(max_age_hours=DATA_MAX_AGE_HOURS)


status = _bootstrap_once()


# ---- 快取查詢（TTL 對齊資料更新頻率；資料更新後可清除快取） ----
@st.cache_data(ttl=DATA_MAX_AGE_HOURS * 3600, show_spinner=False)
def cached_regions():
    return service.list_regions()


@st.cache_data(ttl=DATA_MAX_AGE_HOURS * 3600, show_spinner=False)
def cached_daily(geocode: str):
    return service.get_region_daily(geocode)


@st.cache_data(ttl=DATA_MAX_AGE_HOURS * 3600, show_spinner=False)
def cached_segments(geocode: str):
    return service.get_region_segments(geocode)


@st.cache_data(ttl=DATA_MAX_AGE_HOURS * 3600, show_spinner=False)
def cached_days():
    return service.available_days()


@st.cache_data(ttl=DATA_MAX_AGE_HOURS * 3600, show_spinner=False)
def cached_day_map(day: str):
    return service.get_day_all_regions(day)


# ---- 標題與資料狀態 ----
last_updated = service.last_updated()
subtitle = "資料來源：中央氣象署開放資料（F-D0047-091，逐 12 小時，彙整為每日）"
ui.header(subtitle)

if status.get("demo"):
    st.warning("⚠️ 目前顯示的是**示範資料**（找不到有效授權碼或無法連網），"
               "並非中央氣象署即時預報。設定 CWA_API_KEY 後重新整理即可取得真實資料。")
elif status.get("error"):
    st.info(f"自動更新未成功，顯示的是先前抓取的資料。原因：{status['error']}")

st.caption(f"資料最後更新時間：{last_updated or '尚無資料'}　｜　"
           f"預報單位：每日（由逐 12 小時彙整）")


# ---- 沒有任何資料時的處理 ----
regions = cached_regions()
if not regions:
    st.error("目前沒有可用的預報資料。請確認已設定 CWA_API_KEY，"
             "或執行：py -3.12 update_data.py（本機）／--demo（示範）。")
    st.stop()


# ---- 控制列：地區 + 日期 ----
with st.container(key="controls_card"):
    c1, c2 = st.columns([2, 1])
    with c1:
        labels = [r["label"] for r in regions]
        idx = st.selectbox("選擇縣市", range(len(labels)),
                           format_func=lambda i: labels[i])
        geocode = regions[idx]["geocode"]
    with c2:
        days = cached_days()
        day = st.selectbox("地圖日期", days) if days else None

region_label = labels[idx]
daily_df = cached_daily(geocode)

# ---- 帶傘提醒（首頁明顯位置）----
alert = service.umbrella_alert(daily_df, threshold=UMBRELLA_THRESHOLD)
if alert:
    with st.container(key="alert_card"):
        ui.umbrella_reminder(alert, threshold=UMBRELLA_THRESHOLD)

# ---- 每日高低溫折線圖 ----
with st.container(key="chart_card"):
    st.subheader(f"{region_label}　一週每日高低溫")
    if not daily_df.empty:
        st.caption(f"預報涵蓋日期：{daily_df['day'].min()} ~ {daily_df['day'].max()}")
    ui.daily_temp_chart(daily_df)

# ---- 資料表 ----
with st.container(key="table_card"):
    st.subheader("每日預報資料")
    ui.daily_table(daily_df)
    ui.segments_table(cached_segments(geocode))

# ---- 全台地圖 ----
with st.container(key="map_card"):
    if day:
        st.subheader(f"{day}　全台各縣市當日最高溫")
        ui.taiwan_map(cached_day_map(day))
    else:
        st.info("沒有可用的地圖日期。")
