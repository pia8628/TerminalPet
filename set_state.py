"""手動測試桌寵狀態切換用的小工具。

用法：
    python set_state.py waiting                  寫入名為 manual 的假 session
    python set_state.py working --session b --project 另一個專案
    python set_state.py end --session b          移除該 session
    python set_state.py clear                    移除所有 set_state.py 寫的假 session

可用狀態：idle thinking working waiting done end

正式運作時是 Claude Code 的 hooks 呼叫 scripts/pet-state.sh
（每個 session 各寫一個檔，桌寵每個 session 各顯示一個燈，見 pet.py）。
這支腳本讓你不必真的開好幾個 Claude Code session，也能測試多 session 的顯示。
假 session 的 sid 都以 manual 開頭，clear 只會清掉這些。
"""

import argparse
import json
import time
from pathlib import Path

SESSIONS_DIR = Path.home() / ".terminalpet" / "sessions"
VALID_STATES = ("idle", "thinking", "working", "waiting", "done", "end")


def write_state(state: str, session: str = "manual", project: str | None = None) -> None:
    if state not in VALID_STATES:
        raise ValueError(f"未知狀態：{state}，可用：{VALID_STATES}")
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    target = SESSIONS_DIR / f"{session}.json"
    if state == "end":
        target.unlink(missing_ok=True)
        return

    now = time.time()
    old = {}
    try:
        old = json.loads(target.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    payload = {
        "state": state,
        "ts": now,
        "since": old.get("since", now) if old.get("state") == state else now,
        "start": old.get("start", now),
        "sid": session,
        "project": project or old.get("project") or session,
        "cwd": "",
    }
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(target)


def main():
    parser = argparse.ArgumentParser(description="手動切換桌寵狀態（測試用）")
    parser.add_argument("state", help=f"{' / '.join(VALID_STATES)}，或 clear")
    parser.add_argument("--session", default="manual", help="假 session 名稱（預設 manual）")
    parser.add_argument("--project", help="顯示用的專案名稱（預設同 session 名稱）")
    args = parser.parse_args()

    state = args.state.strip().lower()
    if state == "clear":
        for path in SESSIONS_DIR.glob("manual*.json"):
            path.unlink(missing_ok=True)
        return
    session = args.session if args.session.startswith("manual") else f"manual-{args.session}"
    write_state(state, session, args.project)


if __name__ == "__main__":
    main()
