"""安裝腳本：把桌寵所需的 Claude Code hooks 併入使用者的全域設定。

給不同使用者（不同機器、不同 ~/.claude 路徑）用同一支腳本安裝，
不用手動編輯 settings.json：

    python install.py            安裝／更新桌寵 hooks
    python install.py --dry-run  只印出會做的變更，不實際寫入

會做的事：
    1. 複製 scripts/pet-state.sh 到 ~/.claude/scripts/pet-state.sh
    2. 在 ~/.claude/settings.json 的 hooks 區塊中，於
       PreToolUse / UserPromptSubmit / Notification / Stop / SessionEnd
       各掛一個呼叫 pet-state.sh 的 hook

其他既有設定（permissions、guard-tool.sh、statusLine 等）完全不動。
重複執行是安全的：每次都會先移除舊版桌寵 hook（不論是舊版 printf
寫法或先前裝過的 pet-state.sh），再裝上目前這份腳本對應的版本。
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
CLAUDE_DIR = Path.home() / ".claude"
SETTINGS_PATH = CLAUDE_DIR / "settings.json"
SCRIPTS_DIR = CLAUDE_DIR / "scripts"
PET_STATE_SRC = REPO_DIR / "scripts" / "pet-state.sh"

# hook 事件名稱 -> 觸發時桌寵應顯示的狀態
EVENT_STATE = {
    "PreToolUse": "working",
    "UserPromptSubmit": "thinking",
    "Notification": "waiting",
    "Stop": "done",
    "SessionEnd": "sleeping",
}

# 用來辨識「這個 hook command 是桌寵寫的」，涵蓋舊版與新版寫法，
# 這樣重跑安裝時才能正確替換掉舊的，而不是疊加。
PET_HOOK_MARKERS = ("pet-state.sh", "terminalpet/state.json")


def make_pet_hook_group(state: str) -> dict:
    return {
        "hooks": [
            {
                "type": "command",
                "command": f'bash "$HOME/.claude/scripts/pet-state.sh" {state}',
                "shell": "bash",
                "async": True,
            }
        ]
    }


def merge_hooks(settings: dict) -> list[str]:
    """把桌寵 hook 併入 settings["hooks"]，就地修改，回傳變更說明列表。"""
    changes = []
    hooks = settings.setdefault("hooks", {})
    for event, state in EVENT_STATE.items():
        groups = hooks.setdefault(event, [])
        kept = []
        had_pet_hook = False
        for group in groups:
            cmd_blob = " ".join(h.get("command", "") for h in group.get("hooks", []))
            if any(marker in cmd_blob for marker in PET_HOOK_MARKERS):
                had_pet_hook = True
                continue
            kept.append(group)
        new_group = make_pet_hook_group(state)
        kept.append(new_group)
        if kept != groups:
            changes.append(f"{event}: {'更新' if had_pet_hook else '新增'}桌寵 hook -> {state}")
        hooks[event] = kept
    return changes


def main():
    parser = argparse.ArgumentParser(description="安裝 TerminalPet 的 Claude Code hooks")
    parser.add_argument("--dry-run", action="store_true", help="只顯示會做的變更，不實際寫入")
    args = parser.parse_args()

    if not PET_STATE_SRC.exists():
        print(f"錯誤：找不到 {PET_STATE_SRC}", file=sys.stderr)
        sys.exit(1)

    dest = SCRIPTS_DIR / "pet-state.sh"
    src_text = PET_STATE_SRC.read_text(encoding="utf-8")
    script_changed = not dest.exists() or dest.read_text(encoding="utf-8") != src_text

    if SETTINGS_PATH.exists():
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    else:
        settings = {}

    changes = merge_hooks(settings)
    if script_changed:
        changes.insert(0, f"複製 pet-state.sh -> {dest}")

    if not changes:
        print("已是最新狀態，無需變更。")
        return

    print("將進行以下變更：")
    for c in changes:
        print(f"  - {c}")

    if args.dry_run:
        print("\n(dry-run，未實際寫入)")
        return

    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    if script_changed:
        shutil.copy2(PET_STATE_SRC, dest)
        dest.chmod(0o755)

    SETTINGS_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("\n安裝完成。")


if __name__ == "__main__":
    main()
