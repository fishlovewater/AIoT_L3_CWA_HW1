"""bootstrap.py — 初始化與自動更新。

app.py 啟動時呼叫，確保：
- 資料表存在。
- 若資料庫為空或資料過舊，且有授權碼，就自動抓一次（雲端唯一可行的更新方式）。
- 抓取失敗不讓網站崩潰：沿用現有資料並回報。

回傳 dict 讓 UI 顯示狀態（是否示範資料、錯誤訊息等）。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from backend import database

_TZ = timezone(timedelta(hours=8))


def _older_than(iso_str: Optional[str], hours: float) -> bool:
    if not iso_str:
        return True
    try:
        dt = datetime.fromisoformat(iso_str)
    except ValueError:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_TZ)
    return dt < datetime.now(_TZ) - timedelta(hours=hours)


def ensure_fresh_data(max_age_hours: float = 6.0,
                      allow_demo_fallback: bool = True) -> dict:
    """建表 + 視需要更新。回傳狀態 dict。

    邏輯：
      1. 建表。
      2. 資料夠新 -> 直接用。
      3. 需更新且有授權碼 -> 抓真實資料；失敗則沿用舊資料（若有）。
      4. 完全沒資料且沒授權碼 -> 若 allow_demo_fallback，灌一次示範資料。
    """
    import update_data  # 延遲載入避免循環

    database.init_db()
    last = database.last_fetched_at()
    have_data = database.row_count() > 0

    status = {"updated": False, "demo": False, "error": None,
              "last_fetched": last, "have_data": have_data}

    if have_data and not _older_than(last, max_age_hours):
        return status  # 資料夠新

    # 嘗試真實更新
    report = update_data.run(demo=False)
    if report.ok:
        status.update(updated=True, last_fetched=report.fetched_at,
                      have_data=True)
        return status

    # 真實更新失敗
    status["error"] = report.error
    if have_data:
        return status  # 沿用舊資料

    # 完全沒資料：用示範資料讓 UI 至少能動
    if allow_demo_fallback:
        demo_report = update_data.run(demo=True)
        if demo_report.ok:
            status.update(updated=True, demo=True,
                          last_fetched=demo_report.fetched_at, have_data=True)
    return status
