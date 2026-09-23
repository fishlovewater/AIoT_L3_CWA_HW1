"""frontend/styles.py — 莫蘭迪白色系天氣應用風格。

莫蘭迪色系特徵：高飽和度降低、灰調混入，整體柔霧感、質感高雅。
主色調：米白、灰藕、薄荷霧、灰藍、玫瑰灰——全數降飽和，以白色系為主導。
"""
from __future__ import annotations

import streamlit as st

CARD_KEYS = ["hero_card", "chart_card", "table_card", "map_card"]


def inject_glass_css() -> None:
    card_selectors = ", ".join(f".st-key-{k}" for k in CARD_KEYS)
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Noto+Sans+TC:wght@300;400;500;700&display=swap');

        /* 莫蘭迪背景：純白底 + 多層柔和色光暈，讓毛玻璃有東西可模糊 */
        .stApp {{
            background-color: #f5f3f0 !important;
            background-image:
                radial-gradient(ellipse 70% 55% at 15% 20%, rgba(180, 200, 215, 0.55) 0%, transparent 70%),
                radial-gradient(ellipse 55% 50% at 85% 10%, rgba(208, 195, 210, 0.50) 0%, transparent 65%),
                radial-gradient(ellipse 60% 45% at 75% 75%, rgba(196, 176, 162, 0.42) 0%, transparent 65%),
                radial-gradient(ellipse 50% 55% at 10% 80%, rgba(160, 188, 172, 0.38) 0%, transparent 60%),
                radial-gradient(ellipse 40% 40% at 50% 50%, rgba(230, 225, 218, 0.60) 0%, transparent 70%) !important;
            background-attachment: fixed !important;
            font-family: 'Plus Jakarta Sans', 'Noto Sans TC', -apple-system, BlinkMacSystemFont, sans-serif !important;
            color: #3d3a38 !important;
        }}

        /* 側邊欄：霧白玻璃，邊線細緻 */
        [data-testid="stSidebar"] {{
            background: rgba(255, 253, 250, 0.72) !important;
            backdrop-filter: blur(28px) saturate(140%) !important;
            -webkit-backdrop-filter: blur(28px) saturate(140%) !important;
            border-right: 1px solid rgba(180, 172, 168, 0.30) !important;
        }}
        [data-testid="stSidebar"] * {{
            color: #3d3a38 !important;
        }}
        [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
            color: #5c5552 !important;
        }}
        [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {{
            background: rgba(255, 255, 255, 0.80) !important;
            border: 1px solid rgba(180, 172, 168, 0.45) !important;
            border-radius: 14px !important;
            color: #3d3a38 !important;
        }}
        [data-testid="stSidebar"] .stButton > button {{
            background: linear-gradient(135deg, rgba(200, 193, 188, 0.5) 0%, rgba(220, 215, 212, 0.4) 100%) !important;
            color: #4a4644 !important;
            border: 1px solid rgba(180, 172, 168, 0.55) !important;
            border-radius: 14px !important;
            padding: 8px 16px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
            width: 100% !important;
        }}
        [data-testid="stSidebar"] .stButton > button:hover {{
            background: rgba(200, 193, 188, 0.7) !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 14px rgba(120, 110, 105, 0.18) !important;
        }}
        [data-testid="stSidebar"] .stCaption {{
            color: #8a8380 !important;
        }}

        /* 主畫面液態玻璃容器：高透明 + 強模糊 + 內光邊 */
        {card_selectors} {{
            background: rgba(255, 255, 255, 0.40) !important;
            backdrop-filter: blur(36px) saturate(160%) brightness(1.05) !important;
            -webkit-backdrop-filter: blur(36px) saturate(160%) brightness(1.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.70) !important;
            border-radius: 28px !important;
            box-shadow: 0 8px 32px rgba(120, 110, 105, 0.10), 0 2px 8px rgba(180, 172, 168, 0.10), inset 0 1px 0 rgba(255, 255, 255, 0.80) !important;
            padding: 24px 28px !important;
            margin-bottom: 22px !important;
        }}

        /* Hero 主氣象卡片：高透液態玻璃 + 莫蘭迪霧色漸層光暈 */
        .hero-weather-card {{
            background: linear-gradient(145deg, rgba(200, 215, 225, 0.52) 0%, rgba(215, 208, 222, 0.48) 50%, rgba(222, 212, 205, 0.52) 100%);
            backdrop-filter: blur(40px) saturate(170%) brightness(1.04);
            -webkit-backdrop-filter: blur(40px) saturate(170%) brightness(1.04);
            border: 1px solid rgba(255, 255, 255, 0.80);
            border-radius: 32px;
            box-shadow: 0 16px 48px rgba(100, 95, 92, 0.12), 0 4px 16px rgba(160, 152, 148, 0.14), inset 0 1px 0 rgba(255, 255, 255, 0.90);
            padding: 32px 36px;
            margin-bottom: 22px;
            position: relative;
            overflow: hidden;
        }}
        .hero-top-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        .hero-location-badge {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 1.35rem;
            font-weight: 700;
            color: #3d3a38;
            letter-spacing: 0.3px;
        }}
        .hero-date-badge {{
            font-size: 0.92rem;
            color: #6b6461;
            background: rgba(255, 255, 255, 0.60);
            padding: 6px 14px;
            border-radius: 20px;
            border: 1px solid rgba(210, 205, 200, 0.6);
            backdrop-filter: blur(10px);
        }}
        .hero-main-flex {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 10px 0 22px 0;
        }}
        .hero-temp-number {{
            font-size: 5.6rem;
            font-weight: 800;
            line-height: 1;
            color: #3d3a38;
            letter-spacing: -2px;
            display: flex;
            align-items: flex-start;
        }}
        .hero-temp-unit {{
            font-size: 3.2rem;
            font-weight: 300;
            margin-left: 2px;
            color: #6b6461;
        }}
        .hero-condition-text {{
            font-size: 1.45rem;
            font-weight: 600;
            color: #4a4644;
            margin-top: 6px;
        }}
        .hero-high-low {{
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 1.05rem;
            color: #6b6461;
            margin-top: 8px;
            font-weight: 500;
        }}
        .hero-hl-sep {{ opacity: 0.45; }}
        .hero-icon-col {{
            font-size: 5.5rem;
            line-height: 1;
            filter: drop-shadow(0 6px 16px rgba(100, 95, 92, 0.15));
            user-select: none;
        }}

        /* 天候膠囊提醒 */
        .hero-summary-pill {{
            border-radius: 20px;
            padding: 13px 22px;
            font-size: 1.0rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .hero-summary-pill.pill-rain {{
            background: rgba(196, 176, 162, 0.40);
            border: 1px solid rgba(196, 176, 162, 0.60);
            color: #5a4a40;
        }}
        .hero-summary-pill.pill-sunny {{
            background: rgba(255, 255, 255, 0.55);
            border: 1px solid rgba(210, 205, 200, 0.55);
            color: #5c5552;
        }}

        /* 四格指標小卡 */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 22px;
        }}
        .metric-card {{
            background: rgba(255, 255, 255, 0.68);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(210, 205, 200, 0.50);
            border-radius: 24px;
            padding: 20px 22px;
            box-shadow: 0 4px 16px rgba(120, 110, 105, 0.08);
            display: flex;
            flex-direction: column;
            gap: 6px;
            transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
            background: rgba(255, 255, 255, 0.82);
            box-shadow: 0 8px 24px rgba(120, 110, 105, 0.14);
        }}
        .metric-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.88rem;
            color: #8a8380;
            font-weight: 500;
        }}
        .metric-value {{
            font-size: 2.1rem;
            font-weight: 700;
            color: #3d3a38;
            line-height: 1.15;
        }}
        .metric-desc {{
            font-size: 0.80rem;
            color: #a09d9b;
        }}

        /* 7-Day 天氣微縮卡條 */
        .daily-strip {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 10px;
            margin-top: 18px;
        }}
        .daily-strip-item {{
            background: rgba(255, 255, 255, 0.50);
            border: 1px solid rgba(210, 205, 200, 0.48);
            border-radius: 20px;
            padding: 14px 10px;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
            transition: all 0.2s ease;
        }}
        .daily-strip-item:hover {{
            background: rgba(255, 255, 255, 0.80);
            transform: translateY(-2px);
            box-shadow: 0 6px 18px rgba(120, 110, 105, 0.12);
        }}
        .daily-strip-item.is-selected {{
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(180, 172, 168, 0.70);
            box-shadow: 0 6px 20px rgba(120, 110, 105, 0.14);
        }}
        .daily-strip-day {{
            font-size: 0.88rem;
            font-weight: 700;
            color: #4a4644;
        }}
        .daily-strip-date {{
            font-size: 0.75rem;
            color: #9a9693;
        }}
        .daily-strip-icon {{
            font-size: 1.9rem;
            line-height: 1;
            margin: 4px 0;
        }}
        .daily-strip-temp {{
            font-size: 0.88rem;
            font-weight: 700;
            color: #3d3a38;
        }}
        .daily-strip-pop {{
            font-size: 0.76rem;
            color: #8a9eaa;
            font-weight: 600;
        }}

        /* 章節標題與副標 */
        .section-title {{
            font-size: 1.25rem;
            font-weight: 700;
            color: #3d3a38;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .section-subtitle {{
            font-size: 0.86rem;
            color: #9a9693;
            margin-bottom: 16px;
        }}

        /* 側邊欄溫度圖例 */
        .sidebar-legend-row {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: 10px;
        }}
        .sidebar-legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.86rem;
            color: #6b6461;
        }}
        .sidebar-legend-dot {{
            width: 13px;
            height: 13px;
            border-radius: 50%;
            border: 1px solid rgba(180, 172, 168, 0.45);
            flex-shrink: 0;
        }}

        /* Dataframe 與 Expander 白色毛玻璃 */
        .stDataFrame {{
            background: rgba(255, 255, 255, 0.70) !important;
            border-radius: 16px !important;
            border: 1px solid rgba(210, 205, 200, 0.45) !important;
        }}
        .stExpander {{
            background: rgba(255, 255, 255, 0.55) !important;
            border-radius: 16px !important;
            border: 1px solid rgba(210, 205, 200, 0.45) !important;
        }}
        .stExpander summary {{
            color: #4a4644 !important;
            font-weight: 600 !important;
        }}

        /* 警告與資訊訊息框統一白底 */
        .stAlert {{
            background: rgba(255, 255, 255, 0.70) !important;
            border-radius: 16px !important;
            border: 1px solid rgba(210, 205, 200, 0.50) !important;
            color: #4a4644 !important;
        }}

        /* 隱藏預設裝飾 */
        #MainMenu, footer {{ visibility: hidden; }}
        header {{ background: transparent !important; }}

        /* 主畫面文字 */
        .stMarkdown, .stText, p, span, label {{
            color: #3d3a38 !important;
        }}
        h1, h2, h3, h4 {{
            color: #2e2b29 !important;
        }}

        /* 手機與窄螢幕 */
        @media (max-width: 768px) {{
            .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .daily-strip {{ grid-template-columns: repeat(4, 1fr); }}
            .hero-temp-number {{ font-size: 4.2rem; }}
            .hero-icon-col {{ font-size: 4rem; }}
            .hero-weather-card {{ padding: 22px 20px; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
