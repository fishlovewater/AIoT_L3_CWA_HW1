"""frontend/styles.py — 現代天氣應用風格（Samsung Weather / OpenWeather Glassmorphism）。

設計特點：
- 極致簡潔大氣，以天空藍漸層為背景，大字級溫度展示。
- 真正液態玻璃效果（毛玻璃模糊 + 纖細白邊框 + 環境軟陰影）。
- 側邊欄專屬毛玻璃質感，將所有控制器集中於側邊欄，釋放主畫面。
- 完美適配行動裝置與桌面寬螢幕。
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

        /* 全局大氣天空漸層背景 */
        .stApp {{
            background: linear-gradient(160deg, #1d4e89 0%, #296bb0 30%, #468fd7 65%, #7db8f5 100%) !important;
            background-attachment: fixed !important;
            font-family: 'Plus Jakarta Sans', 'Noto Sans TC', -apple-system, BlinkMacSystemFont, sans-serif !important;
            color: #ffffff !important;
        }}

        /* 側邊欄現代玻璃風格 */
        [data-testid="stSidebar"] {{
            background: rgba(14, 38, 70, 0.55) !important;
            backdrop-filter: blur(28px) saturate(190%) !important;
            -webkit-backdrop-filter: blur(28px) saturate(190%) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.15) !important;
        }}
        [data-testid="stSidebar"] * {{
            color: #ffffff !important;
        }}
        [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {{
            background: rgba(255, 255, 255, 0.15) !important;
            border: 1px solid rgba(255, 255, 255, 0.25) !important;
            border-radius: 14px !important;
            color: #ffffff !important;
        }}
        [data-testid="stSidebar"] .stButton > button {{
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.3) 0%, rgba(255, 255, 255, 0.15) 100%) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.4) !important;
            border-radius: 14px !important;
            padding: 8px 16px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
            width: 100% !important;
        }}
        [data-testid="stSidebar"] .stButton > button:hover {{
            background: rgba(255, 255, 255, 0.4) !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2) !important;
        }}

        /* 主畫面液態玻璃容器 */
        {card_selectors} {{
            background: rgba(255, 255, 255, 0.18) !important;
            backdrop-filter: blur(28px) saturate(190%) !important;
            -webkit-backdrop-filter: blur(28px) saturate(190%) !important;
            border: 1px solid rgba(255, 255, 255, 0.35) !important;
            border-radius: 28px !important;
            box-shadow: 0 16px 40px rgba(10, 30, 60, 0.18) !important;
            padding: 24px 28px !important;
            margin-bottom: 22px !important;
        }}

        /* Hero 主氣象卡片（Samsung Weather 風格） */
        .hero-weather-card {{
            background: rgba(255, 255, 255, 0.18);
            backdrop-filter: blur(32px) saturate(200%);
            -webkit-backdrop-filter: blur(32px) saturate(200%);
            border: 1px solid rgba(255, 255, 255, 0.4);
            border-radius: 32px;
            box-shadow: 0 20px 50px rgba(8, 28, 62, 0.22);
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
            font-size: 1.45rem;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: 0.5px;
        }}
        .hero-date-badge {{
            font-size: 0.95rem;
            color: rgba(255, 255, 255, 0.85);
            background: rgba(255, 255, 255, 0.18);
            padding: 6px 14px;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.25);
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
            color: #ffffff;
            text-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            letter-spacing: -2px;
            display: flex;
            align-items: flex-start;
        }}
        .hero-temp-unit {{
            font-size: 3.2rem;
            font-weight: 300;
            margin-left: 2px;
            color: rgba(255, 255, 255, 0.88);
        }}
        .hero-condition-text {{
            font-size: 1.55rem;
            font-weight: 600;
            color: #ffffff;
            margin-top: 6px;
            text-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }}
        .hero-high-low {{
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 1.15rem;
            color: rgba(255, 255, 255, 0.92);
            margin-top: 8px;
            font-weight: 500;
        }}
        .hero-hl-sep {{ opacity: 0.4; }}
        .hero-icon-col {{
            font-size: 5.5rem;
            line-height: 1;
            filter: drop-shadow(0 10px 20px rgba(0, 0, 0, 0.2));
            user-select: none;
        }}

        /* 溫馨提醒膠囊（Samsung Weather 底部提示膠囊） */
        .hero-summary-pill {{
            border-radius: 20px;
            padding: 13px 22px;
            font-size: 1.02rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 10px;
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            transition: all 0.25s ease;
        }}
        .hero-summary-pill.pill-rain {{
            background: rgba(255, 179, 71, 0.32);
            border: 1px solid rgba(255, 214, 153, 0.6);
            color: #fff9db;
            box-shadow: 0 6px 24px rgba(230, 126, 34, 0.22);
        }}
        .hero-summary-pill.pill-sunny {{
            background: rgba(255, 255, 255, 0.22);
            border: 1px solid rgba(255, 255, 255, 0.4);
            color: #ffffff;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
        }}

        /* 四格指標小卡片（OpenWeather 底部數據格） */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 22px;
        }}
        .metric-card {{
            background: rgba(255, 255, 255, 0.18);
            backdrop-filter: blur(24px) saturate(180%);
            -webkit-backdrop-filter: blur(24px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.35);
            border-radius: 24px;
            padding: 20px 22px;
            box-shadow: 0 12px 30px rgba(10, 30, 60, 0.14);
            display: flex;
            flex-direction: column;
            gap: 6px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
            background: rgba(255, 255, 255, 0.24);
            box-shadow: 0 16px 36px rgba(10, 30, 60, 0.2);
        }}
        .metric-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.92rem;
            color: rgba(255, 255, 255, 0.85);
            font-weight: 500;
        }}
        .metric-value {{
            font-size: 2.1rem;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.15;
        }}
        .metric-desc {{
            font-size: 0.82rem;
            color: rgba(255, 255, 255, 0.72);
        }}

        /* 一週天氣微縮卡條 (7-Day Forecast Strip) */
        .daily-strip {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 10px;
            margin-top: 18px;
        }}
        .daily-strip-item {{
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.22);
            border-radius: 20px;
            padding: 14px 10px;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }}
        .daily-strip-item:hover {{
            background: rgba(255, 255, 255, 0.24);
            transform: translateY(-2px);
        }}
        .daily-strip-item.is-selected {{
            background: rgba(255, 255, 255, 0.28);
            border: 1px solid rgba(255, 255, 255, 0.55);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
        }}
        .daily-strip-day {{
            font-size: 0.88rem;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.95);
        }}
        .daily-strip-date {{
            font-size: 0.76rem;
            color: rgba(255, 255, 255, 0.7);
        }}
        .daily-strip-icon {{
            font-size: 2rem;
            line-height: 1;
            margin: 4px 0;
        }}
        .daily-strip-temp {{
            font-size: 0.92rem;
            font-weight: 700;
            color: #ffffff;
        }}
        .daily-strip-pop {{
            font-size: 0.78rem;
            color: #bee3f8;
            font-weight: 600;
        }}

        /* 標題與副標 */
        .section-title {{
            font-size: 1.35rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .section-subtitle {{
            font-size: 0.88rem;
            color: rgba(255, 255, 255, 0.75);
            margin-bottom: 16px;
        }}

        /* 側邊欄圖例項目 */
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
            font-size: 0.88rem;
            color: rgba(255, 255, 255, 0.9);
        }}
        .sidebar-legend-dot {{
            width: 14px;
            height: 14px;
            border-radius: 50%;
            border: 1px solid rgba(255, 255, 255, 0.4);
            flex-shrink: 0;
        }}

        /* Dataframe 與 Expander 柔和毛玻璃風格 */
        .stDataFrame {{
            background: rgba(255, 255, 255, 0.12) !important;
            border-radius: 18px !important;
            overflow: hidden !important;
            border: 1px solid rgba(255, 255, 255, 0.25) !important;
        }}
        .stExpander {{
            background: rgba(255, 255, 255, 0.12) !important;
            border-radius: 18px !important;
            border: 1px solid rgba(255, 255, 255, 0.25) !important;
        }}
        .stExpander summary {{
            color: #ffffff !important;
            font-weight: 600 !important;
        }}

        /* 隱藏預設多餘 Streamlit 裝飾 */
        #MainMenu, footer {{ visibility: hidden; }}
        header {{ background: transparent !important; }}

        /* 手機與窄螢幕適應 */
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
