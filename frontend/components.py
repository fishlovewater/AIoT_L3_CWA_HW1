"""frontend/components.py — 現代天氣 UI 元件庫（Samsung Weather / OpenWeather 風格）。

特點：
- 極致簡潔大器，大字級溫度展示、動態天候膠囊。
- 所有 HTML 均緊湊拼接輸出，絕無多餘縮排，防止 Markdown 誤判為程式碼區塊（<pre><code>）。
- Altair 高性能向量圖表，平滑曲線與豐富 Hover Tooltip，澈底告別 Matplotlib 缺字問題。
- 專屬 7-Day 天氣微縮條，資訊一覽無遺。
- 支援空資料保護與安全預設值。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import altair as alt
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from data.geo import coords_for

# 地圖溫度分級配色（莫蘭迪降飽和版）
_TEMP_BINS = [
    (20, "#8aafc7", "< 20°C (寒冷)"),
    (25, "#8fb8a2", "20–25°C (舒適)"),
    (30, "#c4a882", "25–30°C (暖熱)"),
    (999, "#c08080", "> 30°C (炎熱)"),
]


def _weekday_str(date_str: str) -> str:
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return weekdays[dt.weekday()]
    except Exception:
        return ""


def _short_weekday(date_str: str) -> str:
    weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return weekdays[dt.weekday()]
    except Exception:
        return date_str


def _weather_meta(max_t: Optional[float], min_t: Optional[float], pop: Optional[float]) -> tuple[str, str, str]:
    """依據高低溫與降雨機率推估代表圖示、天氣文字與說明。"""
    if pop is not None and not pd.isna(pop):
        if pop >= 70:
            return "🌧️", "陰有短暫陣雨", "今日降雨機率高，出門請務必攜帶雨具並注意安全。"
        if pop >= 40:
            return "🌦️", "多雲時陰短暫雨", "局部時段可能有局部短暫雨，建議隨身攜帶折疊傘。"
        if pop >= 20:
            return "⛅", "多雲時晴", "大致舒適多雲，偶有陽光，外出活動適宜。"

    if max_t is not None and not pd.isna(max_t):
        if max_t >= 32:
            return "☀️", "晴朗炎熱", "全天陽光充足、氣溫偏高，戶外活動請注意防曬與補水。"
        if max_t <= 22:
            return "🌤️", "舒適微涼", "天氣偏涼溫和，早晚外出建議加件薄外套。"

    return "🌤️", "晴時多雲", "天氣晴朗穩定，全天溫和舒適，適合各項戶外休閒行程。"


def hero_weather_card(county: str, today_row, alert: Optional[dict] = None) -> None:
    """Samsung Weather 經典大字卡：當前縣市、今日溫度、天候圖示與動態膠囊提醒。"""
    day = getattr(today_row, "day", datetime.now().strftime("%Y-%m-%d"))
    weekday = _weekday_str(day)
    max_t = getattr(today_row, "dayMaxT", None)
    min_t = getattr(today_row, "dayMinT", None)
    pop = getattr(today_row, "dayPop", None)

    display_temp = int(max_t) if max_t is not None and not pd.isna(max_t) else 26
    max_str = f"{int(max_t)}°C" if max_t is not None and not pd.isna(max_t) else "—"
    min_str = f"{int(min_t)}°C" if min_t is not None and not pd.isna(min_t) else "—"
    pop_str = f"{int(pop)}%" if pop is not None and not pd.isna(pop) else "—"

    icon, condition_title, default_desc = _weather_meta(max_t, min_t, pop)

    # 膠囊文字判斷
    if alert and alert.get("max_pop", 0) > 50:
        pill_class = "pill-rain"
        pill_text = f"☔ <b>記得帶傘！</b>今日降雨機率高達 <b>{alert['max_pop']}%</b>，外出請務必攜帶雨具。"
    elif pop is not None and not pd.isna(pop) and pop > 30:
        pill_class = "pill-rain"
        pill_text = f"🌦️ 今日降雨機率約 <b>{int(pop)}%</b>，午後局部可能有短暫陣雨，備傘為宜。"
    else:
        pill_class = "pill-sunny"
        pill_text = f"✨ {default_desc}"

    # 單行拼接 HTML，不帶任何多餘縮排與換行，徹底避免 Markdown 誤認為代碼區塊
    html = (
        f'<div class="hero-weather-card">'
        f'<div class="hero-top-bar">'
        f'<div class="hero-location-badge">📍 {county} · 臺灣</div>'
        f'<div class="hero-date-badge">{day} {weekday}</div>'
        f'</div>'
        f'<div class="hero-main-flex">'
        f'<div class="hero-temp-col">'
        f'<div class="hero-temp-number">{display_temp}<span class="hero-temp-unit">°C</span></div>'
        f'<div class="hero-condition-text">{icon} {condition_title}</div>'
        f'<div class="hero-high-low">'
        f'<span>↑ {max_str}</span>'
        f'<span class="hero-hl-sep">/</span>'
        f'<span>↓ {min_str}</span>'
        f'<span class="hero-hl-sep">·</span>'
        f'<span>💧 降雨機率 {pop_str}</span>'
        f'</div>'
        f'</div>'
        f'<div class="hero-icon-col">{icon}</div>'
        f'</div>'
        f'<div class="hero-summary-pill {pill_class}">{pill_text}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def metrics_grid(today_row) -> None:
    """OpenWeather 四宮格指標卡片：最高溫、最低溫、降雨機率、日夜溫差。"""
    max_t = getattr(today_row, "dayMaxT", None)
    min_t = getattr(today_row, "dayMinT", None)
    pop = getattr(today_row, "dayPop", None)

    max_val = f"{int(max_t)}°C" if max_t is not None and not pd.isna(max_t) else "—"
    min_val = f"{int(min_t)}°C" if min_t is not None and not pd.isna(min_t) else "—"
    pop_val = f"{int(pop)}%" if pop is not None and not pd.isna(pop) else "—"

    if max_t is not None and min_t is not None and not pd.isna(max_t) and not pd.isna(min_t):
        diff = int(max_t - min_t)
        diff_val = f"{diff}°C"
        diff_desc = "早晚溫差顯著" if diff >= 8 else "溫差平穩舒適"
    else:
        diff_val = "—"
        diff_desc = "暫無資料"

    html = (
        f'<div class="metrics-grid">'
        f'<div class="metric-card">'
        f'<div class="metric-header">🌡️ 當日最高溫</div>'
        f'<div class="metric-value">{max_val}</div>'
        f'<div class="metric-desc">預報白天高溫峰值</div>'
        f'</div>'
        f'<div class="metric-card">'
        f'<div class="metric-header">❄️ 當日最低溫</div>'
        f'<div class="metric-value">{min_val}</div>'
        f'<div class="metric-desc">預報清晨夜間低溫</div>'
        f'</div>'
        f'<div class="metric-card">'
        f'<div class="metric-header">💧 降雨機率</div>'
        f'<div class="metric-value">{pop_val}</div>'
        f'<div class="metric-desc">全天降雨可能性最大值</div>'
        f'</div>'
        f'<div class="metric-card">'
        f'<div class="metric-header">📊 晝夜溫差</div>'
        f'<div class="metric-value">{diff_val}</div>'
        f'<div class="metric-desc">{diff_desc}</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def weekly_temp_chart(daily_df: pd.DataFrame) -> None:
    """使用 Altair 渲染流暢折線圖，平滑曲線 + 懸浮 Tooltip，無中文字型缺漏問題。"""
    if daily_df is None or daily_df.empty:
        st.info("此地區目前沒有預報資料。")
        return

    df = daily_df.copy()
    df["display_date"] = df["day"].apply(lambda d: f"{d[5:]} ({_short_weekday(d)})")

    melted = df.melt(
        id_vars=["day", "display_date", "dayPop"],
        value_vars=["dayMaxT", "dayMinT"],
        var_name="temp_type",
        value_name="temperature",
    )
    melted["指標"] = melted["temp_type"].map({"dayMaxT": "最高溫", "dayMinT": "最低溫"})
    melted["溫度"] = melted["temperature"].apply(lambda v: f"{int(v)}°C" if pd.notna(v) else "—")
    melted["降雨機率"] = melted["dayPop"].apply(lambda p: f"{int(p)}%" if pd.notna(p) else "—")

    base = alt.Chart(melted).encode(
        x=alt.X(
            "display_date:N",
            title=None,
            sort=None,
            axis=alt.Axis(
                labelAngle=0,
                labelColor="#6b6461",
                labelFontSize=12,
                domainColor="rgba(180,172,168,0.35)",
                tickColor="rgba(180,172,168,0.35)",
            ),
        ),
        y=alt.Y(
            "temperature:Q",
            title="溫度 (°C)",
            scale=alt.Scale(zero=False, padding=1),
            axis=alt.Axis(
                labelColor="#6b6461",
                titleColor="#4a4644",
                gridColor="rgba(180,172,168,0.22)",
                domainColor="transparent",
            ),
        ),
        color=alt.Color(
            "指標:N",
            scale=alt.Scale(domain=["最高溫", "最低溫"], range=["#c08080", "#8aafc7"]),
            legend=alt.Legend(
                title=None,
                orient="top",
                labelColor="#4a4644",
                labelFontSize=13,
                symbolSize=80,
            ),
        ),
    )

    lines = base.mark_line(interpolate="monotone", strokeWidth=3.5)
    points = base.mark_circle(size=70, opacity=1).encode(
        tooltip=[
            alt.Tooltip("day:N", title="日期"),
            alt.Tooltip("指標:N"),
            alt.Tooltip("溫度:N"),
            alt.Tooltip("降雨機率:N"),
        ]
    )

    chart = (
        (lines + points)
        .properties(height=260)
        .configure_view(strokeWidth=0)
        .configure(background="transparent")
    )
    st.altair_chart(chart, width="stretch")


def daily_forecast_strip(daily_df: pd.DataFrame, selected_day: Optional[str] = None) -> None:
    """iOS / Samsung 風格的 7 日微縮卡條。"""
    if daily_df is None or daily_df.empty:
        return

    items_html = []
    for r in daily_df.itertuples(index=False):
        day = r.day
        weekday = _short_weekday(day)
        max_t = getattr(r, "dayMaxT", None)
        min_t = getattr(r, "dayMinT", None)
        pop = getattr(r, "dayPop", None)
        icon, _, _ = _weather_meta(max_t, min_t, pop)

        temp_str = f"{int(max_t)}° / {int(min_t)}°" if max_t and min_t else "—"
        pop_str = f"💧 {int(pop)}%" if pop is not None and not pd.isna(pop) else ""

        is_sel = "is-selected" if str(day) == str(selected_day) else ""
        items_html.append(
            f'<div class="daily-strip-item {is_sel}">'
            f'<div class="daily-strip-day">{weekday}</div>'
            f'<div class="daily-strip-date">{day[5:]}</div>'
            f'<div class="daily-strip-icon">{icon}</div>'
            f'<div class="daily-strip-temp">{temp_str}</div>'
            f'<div class="daily-strip-pop">{pop_str}</div>'
            f'</div>'
        )

    html = f'<div class="daily-strip">{"".join(items_html)}</div>'
    st.markdown(html, unsafe_allow_html=True)


def taiwan_map(day_df: pd.DataFrame) -> None:
    """全台各縣市當日最高溫地圖，嵌入玻璃卡片。"""
    if day_df is None or day_df.empty:
        st.info("所選日期沒有可用的地圖資料。")
        return

    m = folium.Map(location=[23.7, 121.0], zoom_start=7, tiles="OpenStreetMap")
    plotted = 0
    for row in day_df.itertuples(index=False):
        lat = getattr(row, "lat", None)
        lng = getattr(row, "lng", None)
        if lat is None or lng is None or pd.isna(lat) or pd.isna(lng):
            fallback = coords_for(getattr(row, "geocode", None), getattr(row, "county", None))
            if not fallback:
                continue
            lat, lng = fallback
        day_max = getattr(row, "dayMaxT", None)
        day_min = getattr(row, "dayMinT", None)
        day_pop = getattr(row, "dayPop", None)
        name = getattr(row, "county", None) or getattr(row, "town", None) or "?"

        max_fmt = f"{int(day_max)}°C" if day_max is not None and not pd.isna(day_max) else "—"
        min_fmt = f"{int(day_min)}°C" if day_min is not None and not pd.isna(day_min) else "—"
        pop_fmt = f"{int(day_pop)}%" if day_pop is not None and not pd.isna(day_pop) else "—"

        popup_html = (
            f"<div style='font-family: sans-serif; font-size: 13px; line-height: 1.5; color: #1e293b; min-width: 120px;'>"
            f"<b>{name}</b><br>"
            f"最高溫：<b>{max_fmt}</b><br>"
            f"最低溫：<b>{min_fmt}</b><br>"
            f"降雨機率：<b>{pop_fmt}</b>"
            f"</div>"
        )

        folium.CircleMarker(
            location=[float(lat), float(lng)],
            radius=9,
            color=_color_by_temp(day_max),
            fill=True,
            fill_color=_color_by_temp(day_max),
            fill_opacity=0.88,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{name} ({max_fmt})",
        ).add_to(m)
        plotted += 1

    if plotted == 0:
        st.info("找不到可定位的縣市座標。")
        return
    st_folium(m, width="stretch", height=440, returned_objects=[])


def _color_by_temp(t: Optional[float]) -> str:
    if t is None or pd.isna(t):
        return "#9ca3af"
    for upper, color, _ in _TEMP_BINS:
        if t < upper:
            return color
    return "#ef4444"


def sidebar_legend() -> None:
    """側邊欄簡潔溫度圖例。"""
    items = "".join(
        f'<div class="sidebar-legend-item">'
        f'<span class="sidebar-legend-dot" style="background:{color};"></span>'
        f'{label}</div>'
        for _, color, label in _TEMP_BINS
    )
    items += (
        '<div class="sidebar-legend-item">'
        '<span class="sidebar-legend-dot" style="background:#c8c4c0;"></span>'
        '無資料</div>'
    )
    html = f'<div class="sidebar-legend-row">{items}</div>'
    st.markdown(html, unsafe_allow_html=True)


def daily_table(daily_df: pd.DataFrame) -> None:
    """每日高低溫與降雨機率表格。"""
    if daily_df is None or daily_df.empty:
        st.info("沒有可顯示的資料。")
        return
    show = daily_df.rename(
        columns={
            "day": "日期",
            "dayMinT": "最低溫(°C)",
            "dayMaxT": "最高溫(°C)",
            "dayPop": "降雨機率(%)",
        }
    )
    try:
        st.dataframe(show, width="stretch", hide_index=True)
    except TypeError:
        st.dataframe(show, use_container_width=True, hide_index=True)


def segments_table(seg_df: pd.DataFrame) -> None:
    """原始 12 小時時段資料（折疊式）。"""
    if seg_df is None or seg_df.empty:
        return
    with st.expander("查看原始 12 小時時段預報細節"):
        show = seg_df.rename(
            columns={
                "startTime": "開始時段",
                "endTime": "結束時段",
                "minT": "最低溫(°C)",
                "maxT": "最高溫(°C)",
                "pop": "降雨機率(%)",
            }
        )
        try:
            st.dataframe(show, width="stretch", hide_index=True)
        except TypeError:
            st.dataframe(show, use_container_width=True, hide_index=True)
