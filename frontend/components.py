"""frontend/components.py — 可重用 UI 元件。

所有元件都容忍空資料並顯示友善訊息。地圖優先使用來源提供的經緯度，
缺座標時退回 data/geo.py 的備援對照表。
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")  # 無視窗環境（含雲端）安全
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium

from data.geo import coords_for

# 地圖溫度分級（以「當日最高溫」上色）
_TEMP_BINS = [
    (20, "#3b82f6", "< 20°C"),
    (25, "#22c55e", "20–25°C"),
    (30, "#f59e0b", "25–30°C"),
    (999, "#ef4444", "> 30°C"),
]


def _color_by_temp(t: Optional[float]) -> str:
    if t is None or pd.isna(t):
        return "#9ca3af"  # 灰：無資料
    for upper, color, _ in _TEMP_BINS:
        if t < upper:
            return color
    return "#ef4444"


def header(subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="glass-header">
            <h1>☀️ 台灣天氣預報</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def daily_temp_chart(daily_df: pd.DataFrame) -> None:
    """每日最高/最低溫折線圖。X 軸為日期。"""
    if daily_df is None or daily_df.empty:
        st.info("此地區目前沒有可顯示的預報資料。")
        return
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.plot(daily_df["day"], daily_df["dayMaxT"], marker="o",
            color="#ef4444", label="每日最高溫")
    ax.plot(daily_df["day"], daily_df["dayMinT"], marker="o",
            color="#3b82f6", label="每日最低溫")
    ax.set_ylabel("°C")
    ax.set_xlabel("日期")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def daily_table(daily_df: pd.DataFrame) -> None:
    """每日高低溫與降雨機率表格。"""
    if daily_df is None or daily_df.empty:
        st.info("沒有可顯示的資料。")
        return
    show = daily_df.rename(columns={
        "day": "日期",
        "dayMinT": "最低溫(°C)",
        "dayMaxT": "最高溫(°C)",
        "dayPop": "降雨機率(%)",
    })
    st.dataframe(show, use_container_width=True, hide_index=True)


def segments_table(seg_df: pd.DataFrame) -> None:
    """原始 12 小時時段資料（可折疊，供進階檢視）。"""
    if seg_df is None or seg_df.empty:
        return
    with st.expander("查看原始 12 小時時段資料"):
        show = seg_df.rename(columns={
            "startTime": "起", "endTime": "訖",
            "minT": "最低溫", "maxT": "最高溫", "pop": "降雨機率(%)",
        })
        st.dataframe(show, use_container_width=True, hide_index=True)


def umbrella_reminder(alert: Optional[dict], threshold: int = 50) -> None:
    """帶傘提醒卡。alert 為 service.umbrella_alert 的輸出（或 None）。"""
    if not alert:
        return
    days = "、".join(alert["days"][:5])
    st.markdown(
        f'<div class="glass-warn">☔ <b>記得帶傘！</b> '
        f'最高降雨機率 <b>{alert["max_pop"]}%</b>（門檻 {threshold}%）。'
        f'較可能降雨日期：{days}</div>',
        unsafe_allow_html=True,
    )


def temp_legend() -> None:
    """地圖溫度顏色圖例。"""
    items = "".join(
        f'<div class="legend-item"><span class="legend-dot" '
        f'style="background:{color}"></span>{label}</div>'
        for _, color, label in _TEMP_BINS
    )
    items += ('<div class="legend-item"><span class="legend-dot" '
              'style="background:#9ca3af"></span>無資料</div>')
    st.markdown(
        f'<div class="legend-row">{items}</div>'
        '<div style="font-size:.82rem;color:#33506b;margin-top:4px;">'
        '顏色代表各縣市「當日最高溫」。</div>',
        unsafe_allow_html=True,
    )


def taiwan_map(day_df: pd.DataFrame) -> None:
    """全台各縣市當日最高溫地圖。優先用來源經緯度，缺則用備援對照表。"""
    if day_df is None or day_df.empty:
        st.info("所選日期沒有預報資料。")
        return

    m = folium.Map(location=[23.7, 121.0], zoom_start=7, tiles="OpenStreetMap")
    plotted = 0
    for row in day_df.itertuples(index=False):
        lat = getattr(row, "lat", None)
        lng = getattr(row, "lng", None)
        if lat is None or lng is None or pd.isna(lat) or pd.isna(lng):
            fallback = coords_for(getattr(row, "geocode", None),
                                  getattr(row, "county", None))
            if not fallback:
                continue
            lat, lng = fallback
        day_max = getattr(row, "dayMaxT", None)
        day_min = getattr(row, "dayMinT", None)
        day_pop = getattr(row, "dayPop", None)
        name = getattr(row, "county", None) or getattr(row, "town", None) or "?"
        popup = (f"{name}<br>最高 {_fmt(day_max)}°C / 最低 {_fmt(day_min)}°C"
                 f"<br>降雨機率 {_fmt(day_pop)}%")
        folium.CircleMarker(
            location=[float(lat), float(lng)],
            radius=9,
            color=_color_by_temp(day_max),
            fill=True,
            fill_color=_color_by_temp(day_max),
            fill_opacity=0.85,
            popup=folium.Popup(popup, max_width=200),
            tooltip=name,
        ).add_to(m)
        plotted += 1

    if plotted == 0:
        st.info("找不到可定位的縣市座標。")
        return
    st_folium(m, use_container_width=True, height=460, returned_objects=[])
    temp_legend()


def _fmt(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    return str(int(v))
