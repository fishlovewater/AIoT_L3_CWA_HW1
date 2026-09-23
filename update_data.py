"""update_data.py — 抓取 CWA 資料並寫入資料庫。

特性（對應專案指令）：
- 可重複執行：靠唯一鍵 upsert，不新增重複列。
- 失敗保留上一批可用資料：抓取/解析/驗證任一步失敗就不動資料庫。
- 輸出寫入筆數、更新時間與可診斷錯誤；不輸出授權碼。
- 資料庫位置可用環境變數 WEATHER_DB_PATH 設定（見 backend/database.py）。

用法：
    py -3.12 update_data.py            # 從真實 API 抓取
    py -3.12 update_data.py --demo     # 用示範資料（不需授權碼，標示為示範）
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

from backend import fetcher, database

# 台灣時區（+08:00），用來標記抓取時間
_TZ = timezone(timedelta(hours=8))


def _load_local_env() -> None:
    """本機載入 .env；雲端用 st.secrets，缺 dotenv 也不會壞。"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


@dataclass
class UpdateReport:
    ok: bool
    written: int = 0
    skipped: int = 0
    fetched_at: Optional[str] = None
    error: Optional[str] = None
    notes: Optional[list] = None
    demo: bool = False

    def summary(self) -> str:
        if self.ok:
            tag = "（示範資料）" if self.demo else ""
            msg = f"更新成功{tag}：寫入 {self.written} 筆，略過 {self.skipped} 筆，時間 {self.fetched_at}"
            if self.notes:
                msg += " | " + "；".join(self.notes)
            return msg
        return f"更新失敗，已保留現有資料：{self.error}"


def run(demo: bool = False, path: Optional[str] = None) -> UpdateReport:
    """執行一次更新。回傳 UpdateReport。失敗時不動資料庫。"""
    database.init_db(path)
    fetched_at = datetime.now(_TZ).isoformat(timespec="seconds")

    try:
        if demo:
            from tests.fixtures.demo_data import demo_parse_result
            result = demo_parse_result()
            fetcher.validate(result)
        else:
            _load_local_env()
            result = fetcher.fetch_and_parse()
    except fetcher.FetchError as exc:
        return UpdateReport(ok=False, error=str(exc), demo=demo)
    except Exception as exc:  # 其他非預期錯誤，仍不動資料庫
        return UpdateReport(ok=False, error=f"{type(exc).__name__}: {exc}", demo=demo)

    # 驗證通過才寫入（不會以空資料覆寫）
    written = database.save(result.records, fetched_at, path=path)
    return UpdateReport(
        ok=True,
        written=written,
        skipped=result.skipped,
        fetched_at=fetched_at,
        notes=result.notes or None,
        demo=demo,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="更新台灣天氣預報資料庫")
    parser.add_argument("--demo", action="store_true",
                        help="使用示範資料（不需授權碼；資料標示為示範，非即時預報）")
    args = parser.parse_args(argv)

    report = run(demo=args.demo)
    print(report.summary())
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
