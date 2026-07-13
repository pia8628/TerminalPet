"""手動測試桌寵狀態切換用的小工具。

用法：
    python set_state.py thinking
    python set_state.py working
    python set_state.py waiting
    python set_state.py done
    python set_state.py sleeping

正式運作時 Claude Code 的 hooks 是呼叫 scripts/pet-state.sh
（每個 session 各寫一個檔，桌寵取優先級最高者顯示，見 pet.py）。
這支腳本只寫一個名為 "manual" 的假 session，方便你在終端機手動
切換狀態測試桌寵外觀，不需要真的跑一個 Claude Code session。
"""

import json
import sys
import time
from pathlib import Path

SESSIONS_DIR = Path.home() / ".terminalpet" / "sessions"
VALID_STATES = {"thinking", "working", "waiting", "done", "sleeping"}


def write_state(state: str) -> None:
    if state not in VALID_STATES:
        raise ValueError(f"未知狀態：{state}，可用：{sorted(VALID_STATES)}")
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"state": state, "ts": time.time(), "sid": "manual"}
    target = SESSIONS_DIR / "manual.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(target)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    write_state(sys.argv[1].strip().lower())
