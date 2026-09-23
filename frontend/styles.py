"""frontend/styles.py — iOS 液態玻璃（Liquid Glass）樣式注入。

設計原則：
- 用帶 key 的 st.container 產生穩定 class（st-key-<key>），對它套玻璃樣式，
  而非用跨多次 st.markdown 的開關 <div>（那無法可靠包住 Streamlit 元件）。
- 盡量少依賴 Streamlit 內部 DOM 選擇器；主要以 .st-key-* 這種穩定 hook。
- 半透明 + 背景模糊 + 大圓角 + 柔和陰影；文字用深色確保對比（WCAG AA）。
- 響應式：卡片寬度自適應，手機與桌面皆可用。
"""
from __future__ import annotations

import streamlit as st

# 各卡片使用的 container key（app.py 需用相同 key）
CARD_KEYS = ["controls_card", "alert_card", "chart_card", "table_card", "map_card"]


def inject_glass_css() -> None:
    card_selectors = ", ".join(f".st-key-{k}" for k in CARD_KEYS)
    st.markdown(
        f"""
        <style>
        /* 頁面背景：柔和漸層，突顯玻璃透明感 */
        .stApp {{
            background: linear-gradient(135deg, #a8c9ff 0%, #c8e6ff 45%, #d9f6e6 100%);
            background-attachment: fixed;
        }}

        /* 液態玻璃卡片（套在帶 key 的 container 上） */
        {card_selectors} {{
            background: rgba(255, 255, 255, 0.28);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.45);
            border-radius: 22px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.18);
            padding: 18px 22px;
            margin-bottom: 16px;
        }}

        /* 標題玻璃橫幅 */
        .glass-header {{
            background: rgba(255, 255, 255, 0.35);
            -webkit-backdrop-filter: blur(26px) saturate(180%);
            backdrop-filter: blur(26px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.5);
            border-radius: 26px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.18);
            padding: 20px 24px;
            margin-bottom: 14px;
            color: #16324f;
        }}
        .glass-header h1 {{ margin: 0; font-size: 1.7rem; color: #16324f; }}
        .glass-header p  {{ margin: 4px 0 0; color: #33506b; font-size: .95rem; }}

        /* 帶傘提醒警示卡（暖色、深色字，對比足夠） */
        .glass-warn {{
            background: rgba(255, 209, 102, 0.42);
            -webkit-backdrop-filter: blur(16px) saturate(160%);
            backdrop-filter: blur(16px) saturate(160%);
            border: 1px solid rgba(255, 255, 255, 0.55);
            border-radius: 18px;
            box-shadow: 0 6px 22px rgba(180, 120, 20, 0.22);
            padding: 14px 18px;
            color: #4a3200;
            font-size: 1.05rem;
        }}

        /* 地圖溫度圖例 */
        .legend-row {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 6px; }}
        .legend-item {{ display: flex; align-items: center; gap: 6px; color: #16324f;
                        font-size: .9rem; }}
        .legend-dot {{ width: 14px; height: 14px; border-radius: 50%;
                       border: 1px solid rgba(0,0,0,.15); }}

        /* 窄螢幕：縮小內距 */
        @media (max-width: 640px) {{
            {card_selectors} {{ padding: 14px 14px; border-radius: 18px; }}
            .glass-header h1 {{ font-size: 1.35rem; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
