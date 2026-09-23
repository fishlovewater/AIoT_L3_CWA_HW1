"""api/forecast.py — Vercel Python serverless function。

回傳前端所需的完整天氣資料 JSON（地區清單、每地區每日高低溫與降雨機率、座標、
可用日期）。授權碼從環境變數 CWA_API_KEY 取得，絕不回傳給前端。

Vercel 會把 /api/forecast.py 對應到路徑 /api/forecast。
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler

# 同目錄的共用模組
try:
    from ._cwa import build_payload, CwaError
except ImportError:  # Vercel 以檔案為模組載入時的退路
    import os
    import sys
    sys.path.append(os.path.dirname(__file__))
    from _cwa import build_payload, CwaError  # type: ignore


class handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (Vercel 要求此命名)
        try:
            payload = build_payload()
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            # 邊緣快取 30 分鐘，並允許 stale 期間背景更新
            self.send_header("Cache-Control",
                             "public, max-age=0, s-maxage=1800, stale-while-revalidate=3600")
            self.end_headers()
            self.wfile.write(body)
        except CwaError as exc:
            self._error(502, str(exc))
        except Exception as exc:  # 不洩漏內部細節與金鑰
            self._error(500, f"伺服器錯誤：{type(exc).__name__}")

    def _error(self, code: int, message: str):
        body = json.dumps({"success": False, "error": message},
                          ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)
