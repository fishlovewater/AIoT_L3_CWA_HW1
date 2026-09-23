"""app.py — Vercel Python 入口（WSGI）。

Vercel 新版 Python builder 會把整個專案當成單一 Python 應用，並尋找根目錄
`app.py` 中的 `app` / `application` / `handler`。這裡提供一個純標準庫的 WSGI app，
同時負責：
  - GET /api/forecast  -> 回天氣 JSON（重用 api/_cwa.py 的邏輯）
  - 其他路徑           -> 服務 public/ 內的靜態前端（index.html / app.js / styles.css）

注意：這個 app.py 是「Vercel 版」的入口，與 Streamlit 版無關。
Streamlit 版的進入點是 streamlit_app.py。
"""
from __future__ import annotations

import json
import os
import mimetypes

# 讓 api 套件可被匯入
import sys
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from api._cwa import build_payload, CwaError  # noqa: E402

PUBLIC_DIR = os.path.join(_ROOT, "public")


def _json_response(start_response, status, obj, extra_headers=None):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    headers = [("Content-Type", "application/json; charset=utf-8"),
               ("Content-Length", str(len(body)))]
    if extra_headers:
        headers.extend(extra_headers)
    start_response(status, headers)
    return [body]


def _static_response(start_response, path):
    """服務 public/ 內的靜態檔。path 為 URL 路徑（以 / 開頭）。"""
    rel = path.lstrip("/")
    if rel == "":
        rel = "index.html"
    # 防目錄跳脫
    full = os.path.normpath(os.path.join(PUBLIC_DIR, rel))
    if not full.startswith(PUBLIC_DIR) or not os.path.isfile(full):
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Not Found"]
    ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
    with open(full, "rb") as f:
        body = f.read()
    start_response("200 OK", [("Content-Type", ctype),
                              ("Content-Length", str(len(body)))])
    return [body]


def app(environ, start_response):
    """WSGI 進入點。"""
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET").upper()

    if path == "/api/forecast":
        if method != "GET":
            return _json_response(start_response, "405 Method Not Allowed",
                                  {"success": False, "error": "只接受 GET"})
        try:
            payload = build_payload()
            return _json_response(
                start_response, "200 OK", payload,
                extra_headers=[("Cache-Control",
                                "public, max-age=0, s-maxage=1800, "
                                "stale-while-revalidate=3600")],
            )
        except CwaError as exc:
            return _json_response(start_response, "502 Bad Gateway",
                                  {"success": False, "error": str(exc)})
        except Exception as exc:  # 不洩漏內部細節與金鑰
            return _json_response(start_response, "500 Internal Server Error",
                                  {"success": False,
                                   "error": f"伺服器錯誤：{type(exc).__name__}"})

    # 其他路徑 -> 靜態前端
    return _static_response(start_response, path)


# 常見別名，確保 Vercel 不論找哪個都能對應
application = app
handler = app
