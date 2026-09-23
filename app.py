"""app.py — 現代台灣天氣預報 Web 應用（Samsung Weather / OpenWeather 液態玻璃風格）。

架構：
- 簡約大器主畫面，全功能控制項完整收納至側邊欄（st.sidebar）。
- 主畫面以「Hero 氣象卡 + 四格核心數據 + Altair 7日平滑曲線 + 7日微縮卡 + 互動地圖與時段表」構成。
- 前端只透過 backend.service 取得資料。
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

st.set_page_config(
    page_title="台灣天氣預報",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_glass_css()


# ---- 資料初始化與自動更新 ----
@st.cache_resource(show_spinner="正在同步中央氣象署資料…")
def _bootstrap_once():
    return ensure_fresh_data(max_age_hours=DATA_MAX_AGE_HOURS)


status = _bootstrap_once()


# ---- 快取查詢 ----
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


# ---- 讀取基礎資料 ----
regions = cached_regions()
if not regions:
    st.error("目前沒有可用的預報資料。請確認已設定 CWA_API_KEY，或執行 update_data.py --demo。")
    st.stop()

days = cached_days()
last_updated = service.last_updated()


# ===========================================================================
# 側邊欄控制中心（Sidebar Controls）
# ===========================================================================
with st.sidebar:
    st.markdown("## 🌦️ 台灣天氣預報")
    st.caption("Taiwan Weather · Modern Glass Edition")
    st.markdown("---")

    # 1. 選擇地區
    st.markdown("### 📍 觀測地區")
    labels = [r["label"] for r in regions]
    # 預設選中臺北市（若有）
    default_idx = 0
    for i, lbl in enumerate(labels):
        if "臺北" in lbl or "台北" in lbl:
            default_idx = i
            break
    idx = st.selectbox(
        "選擇縣市",
        range(len(labels)),
        index=default_idx,
        format_func=lambda i: labels[i],
        label_visibility="collapsed",
    )
    selected_region = regions[idx]
    geocode = selected_region["geocode"]
    region_label = selected_region["label"]

    # 2. 選擇日期
    st.markdown("### 📅 檢視日期")
    day = st.selectbox(
        "選擇日期",
        days,
        index=0 if days else None,
        label_visibility="collapsed",
    ) if days else None

    st.markdown("---")

    # 3. 數據同步與控制
    st.markdown("### ⚙️ 資料狀態與同步")
    if st.button("🔄 立即同步最新氣象資料"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

    update_text = last_updated[:16].replace("T", " ") if last_updated else "暫無資料"
    st.caption(f"⏱️ 最後同步：{update_text}")
    st.caption("📡 來源：中央氣象署 F-D0047-091")

    if status.get("demo"):
        st.warning("⚠️ 示範資料模式\n(未配置有效 API Key)")
    elif status.get("error"):
        st.info(f"ℹ️ 沿用已存資料：{status['error']}")

    st.markdown("---")

    # 4. 地圖溫度圖例
    st.markdown("### 🗺️ 地圖溫度標示")
    ui.sidebar_legend()


# ===========================================================================
# 主畫面（Main Page Content）
# ===========================================================================
daily_df = cached_daily(geocode)
if daily_df.empty:
    st.warning("此地區目前尚無預報數據。")
    st.stop()

# 取得所選日期或首日的數據列
target_row = daily_df.iloc[0]
if day:
    match = daily_df[daily_df["day"] == str(day)]
    if not match.empty:
        target_row = match.iloc[0]

# 帶傘警示判斷
alert = service.umbrella_alert(daily_df, threshold=UMBRELLA_THRESHOLD, day=day)

# 1. Hero 頂級天氣主卡（Samsung Weather 風格）
ui.hero_weather_card(county=region_label, today_row=target_row, alert=alert)

# 2. 四格核心天候指標卡（OpenWeather 風格）
ui.metrics_grid(target_row)

# 3. 未來一週每日氣溫平滑曲線與 7 日微縮卡（Altair 向量渲染）
with st.container(key="chart_card"):
    st.markdown('<div class="section-title">📈 未來一週氣溫趨勢</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-subtitle">{region_label} 一週最高溫與最低溫平滑預測曲線（懸浮檢視詳細數據）</div>',
        unsafe_allow_html=True,
    )
    ui.weekly_temp_chart(daily_df)
    ui.daily_forecast_strip(daily_df, selected_day=day)

# 4. 全台各縣市氣溫地圖與詳細時段數據表（左右兩欄分配）
col_map, col_table = st.columns([7, 5])

with col_map:
    with st.container(key="map_card"):
        st.markdown(
            f'<div class="section-title">🗺️ 全台溫度分布圖</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="section-subtitle">檢視日期：{day or "今日"}（依各縣市最高溫著色）</div>',
            unsafe_allow_html=True,
        )
        if day:
            ui.taiwan_map(cached_day_map(day))
        else:
            st.info("沒有可用的地圖日期。")

with col_table:
    with st.container(key="table_card"):
        st.markdown('<div class="section-title">📋 每日預報數據</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="section-subtitle">{region_label} 每日數值與時段拆解</div>', unsafe_allow_html=True)
        ui.daily_table(daily_df)
        ui.segments_table(cached_segments(geocode))
