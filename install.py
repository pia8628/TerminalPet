"""安裝腳本：把桌寵所需的 Claude Code hooks 併入使用者的全域設定。

給不同使用者（不同機器、不同 ~/.claude 路徑）用同一支腳本安裝，
不用手動編輯 settings.json：

    python install.py              安裝／更新桌寵 hooks
    python install.py --dry-run    只印出會做的變更，不實際寫入
    python install.py --uninstall  移除桌寵 hooks 與 pet-state.sh

會做的事：
    1. 複製 scripts/pet-state.sh 到 ~/.claude/scripts/pet-state.sh
    2. 在 ~/.claude/settings.json 的 hooks 區塊中，於 EVENT_STATE 列出的
       每個事件各掛一個呼叫 pet-state.sh 的 hook

（也可以改用 Claude Code plugin 安裝 hooks，見 README；兩種方式擇一即可。）

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
# 與 hooks/hooks.json（plugin 版）保持一致。
EVENT_STATE = {
    "SessionStart": "idle",          # 新 session 一開就出現在燈列
    "UserPromptSubmit": "thinking",
    "PreToolUse": "working",         # AskUserQuestion / ExitPlanMode 由腳本改判 waiting
    "PostToolUse": "working",        # 批准後工具跑完，把紅燈切回執行中
    "PermissionRequest": "waiting",  # 權限對話框出現的當下
    "Notification": "waiting",       # 備援：部分 Windows 環境 PermissionRequest 外的提示
    "Stop": "done",
    "SessionEnd": "end",             # 刪掉該 session 的狀態檔
}

# 事件的 matcher（沒列的事件不設，匹配全部）。
# Notification 涵蓋多種通知：permission_prompt（等你批准）、idle_prompt（閒置
# 60 秒等輸入）、auth_success…等。紅燈只該在「真的需要介入」時亮，
# 不過濾的話，每次收工閒置 60 秒就會被 idle_prompt 點成紅燈。
EVENT_MATCHER = {
    "Notification": "permission_prompt|elicitation_dialog|agent_needs_input",
}

# 用來辨識「這個 hook command 是桌寵寫的」，涵蓋舊版與新版寫法，
# 這樣重跑安裝時才能正確替換掉舊的，而不是疊加。
PET_HOOK_MARKERS = ("pet-state.sh", "terminalpet/state.json")


def make_pet_hook_group(event: str, state: str,
                        script: str = "$HOME/.claude/scripts/pet-state.sh") -> dict:
    group = {
        "hooks": [
            {
                "type": "command",
                "command": f'bash "{script}" {state}',
                "shell": "bash",
                "async": True,
            }
        ]
    }
    if event in EVENT_MATCHER:
        group = {"matcher": EVENT_MATCHER[event], **group}
    return group


def _is_pet_group(group: dict) -> bool:
    cmd_blob = " ".join(h.get("command", "") for h in group.get("hooks", []))
    return any(marker in cmd_blob for marker in PET_HOOK_MARKERS)


def remove_hooks(settings: dict) -> list[str]:
    """移除所有桌寵 hook（不論事件），就地修改，回傳變更說明列表。"""
    changes = []
    hooks = settings.get("hooks", {})
    for event in list(hooks):
        groups = hooks[event]
        kept = [g for g in groups if not _is_pet_group(g)]
        if len(kept) != len(groups):
            changes.append(f"{event}: 移除桌寵 hook")
            if kept:
                hooks[event] = kept
            else:
                del hooks[event]
    return changes


def merge_hooks(settings: dict) -> list[str]:
    """把桌寵 hook 併入 settings["hooks"]，就地修改，回傳變更說明列表。"""
    changes = []
    hooks = settings.setdefault("hooks", {})
    # 先清掉「舊版有掛、新版已不用」事件上的桌寵 hook
    for event in [e for e in hooks if e not in EVENT_STATE]:
        kept = [g for g in hooks[event] if not _is_pet_group(g)]
        if len(kept) != len(hooks[event]):
            changes.append(f"{event}: 移除已不使用的桌寵 hook")
            if kept:
                hooks[event] = kept
            else:
                del hooks[event]
    for event, state in EVENT_STATE.items():
        groups = hooks.setdefault(event, [])
        kept = []
        insert_at = None
        for group in groups:
            if _is_pet_group(group):
                # 原位替換，不改變與其他 hook 的相對順序，重跑時 diff 才乾淨
                if insert_at is None:
                    insert_at = len(kept)
                continue
            kept.append(group)
        had_pet_hook = insert_at is not None
        new_group = make_pet_hook_group(event, state)
        kept.insert(len(kept) if insert_at is None else insert_at, new_group)
        if kept != groups:
            changes.append(f"{event}: {'更新' if had_pet_hook else '新增'}桌寵 hook -> {state}")
        hooks[event] = kept
    return changes


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    return {}


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    # 先備份，萬一寫壞還能還原
    if SETTINGS_PATH.exists():
        shutil.copy2(SETTINGS_PATH, SETTINGS_PATH.with_suffix(".json.terminalpet.bak"))
    SETTINGS_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def report(changes: list[str], dry_run: bool) -> bool:
    """印出變更；回傳 True 代表要繼續實際寫入。"""
    if not changes:
        print("已是最新狀態，無需變更。")
        return False
    print("將進行以下變更：")
    for c in changes:
        print(f"  - {c}")
    if dry_run:
        print("\n(dry-run，未實際寫入)")
        return False
    return True


def uninstall(dry_run: bool) -> None:
    settings = load_settings()
    changes = remove_hooks(settings)
    dest = SCRIPTS_DIR / "pet-state.sh"
    if dest.exists():
        changes.append(f"刪除 {dest}")
    if not report(changes, dry_run):
        return
    save_settings(settings)
    if dest.exists():
        dest.unlink()
    print("\n已移除。~/.terminalpet/ 資料夾保留（內含桌寵設定），不需要可自行刪除。")


def plugin_hooks() -> dict:
    """plugin 版 hooks/hooks.json 的內容（腳本路徑改用 ${CLAUDE_PLUGIN_ROOT}）。"""
    return {"hooks": {
        event: [make_pet_hook_group(event, state, "${CLAUDE_PLUGIN_ROOT}/scripts/pet-state.sh")]
        for event, state in EVENT_STATE.items()
    }}


def export_plugin_hooks() -> None:
    path = REPO_DIR / "hooks" / "hooks.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(plugin_hooks(), indent=2) + "\n", encoding="utf-8")
    print(f"已更新 {path}")


def main():
    # 非中文語系的 Windows 主控台印中文會丟 UnicodeEncodeError，改成以 ? 替代
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="安裝 TerminalPet 的 Claude Code hooks")
    parser.add_argument("--dry-run", action="store_true", help="只顯示會做的變更，不實際寫入")
    parser.add_argument("--uninstall", action="store_true", help="移除桌寵 hooks 與 pet-state.sh")
    parser.add_argument("--export-plugin-hooks", action="store_true",
                        help="（開發用）依 EVENT_STATE 重新產生 plugin 版 hooks/hooks.json")
    args = parser.parse_args()

    if args.export_plugin_hooks:
        export_plugin_hooks()
        return
    if args.uninstall:
        uninstall(args.dry_run)
        return

    if not PET_STATE_SRC.exists():
        print(f"錯誤：找不到 {PET_STATE_SRC}", file=sys.stderr)
        sys.exit(1)

    dest = SCRIPTS_DIR / "pet-state.sh"
    src_text = PET_STATE_SRC.read_text(encoding="utf-8")
    script_changed = not dest.exists() or dest.read_text(encoding="utf-8") != src_text

    settings = load_settings()
    changes = merge_hooks(settings)
    if script_changed:
        changes.insert(0, f"複製 pet-state.sh -> {dest}")

    if not report(changes, args.dry_run):
        return

    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    if script_changed:
        shutil.copy2(PET_STATE_SRC, dest)
        dest.chmod(0o755)
    save_settings(settings)
    print("\n安裝完成。請重啟 Claude Code session（或開一次 /hooks）讓新 hooks 生效。")


if __name__ == "__main__":
    main()
