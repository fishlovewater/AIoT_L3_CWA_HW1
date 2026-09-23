@echo off
chcp 65001 >nul
title 台灣天氣預報 (Taiwan Weather Forecast)
echo ========================================================
echo   啟動台灣天氣預報應用程式 (Streamlit + CWA)
echo ========================================================
echo.
python -m streamlit run streamlit_app.py
pause
