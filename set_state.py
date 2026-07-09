"""寫入桌寵狀態檔的單一入口。

用法：
    python set_state.py thinking
    python set_state.py working
    python set_state.py waiting
    python set_state.py done
    python set_state.py sleeping

Claude Code 的 hooks 也是呼叫這支腳本來更新狀態，
桌寵視窗（pet.py）會定時讀取這個狀態檔並切換表情。
"""

import json
import sys
import time
from pathlib import Path

# 狀態檔位置：放在使用者家目錄下的專屬資料夾，
# 這樣不論從哪個專案觸發 hook 都能寫到同一個檔。
STATE_FILE = Path.home() / ".terminalpet" / "state.json"

VALID_STATES = {"thinking", "working", "waiting", "done", "sleeping"}


def write_state(state: str) -> None:
    if state not in VALID_STATES:
        raise ValueError(f"未知狀態：{state}，可用：{sorted(VALID_STATES)}")
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"state": state, "ts": time.time()}
    STATE_FILE.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    write_state(sys.argv[1].strip().lower())
