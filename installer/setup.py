"""TerminalPet 安裝／解除安裝程式。

雙擊即可執行（打包後為 Setup-TerminalPet.exe）。負責：
    1. 把發行包內容搬到固定位置 %LOCALAPPDATA%\\TerminalPet
    2. 把桌寵狀態 hook 安全合併進使用者的 ~/.claude/settings.json
       （絕不整份覆蓋，只新增／更新自己那幾條，其餘設定原封不動）
    3.（可選）設定開機自動啟動
    4. 解除安裝時用同一套指紋規則反向清除，且只清自己加的部分
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# 打包成 exe 後會在使用者電腦的主控台執行；若對方主控台不是 UTF-8 編碼，
# print() 中文字串會丟 UnicodeEncodeError 讓安裝程式直接當掉。
# 這裡切換主控台編碼到 UTF-8，並讓 stdout/stderr 用 errors="replace" 兜底，
# 即使切換失敗也不會因為印中文而崩潰。
if sys.platform == "win32":
    try:
        subprocess.run(["chcp", "65001"], shell=True, capture_output=True, check=False)
    except OSError:
        pass
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

# ---- 路徑常數 ----
if getattr(sys, "frozen", False):
    SRC_ROOT = Path(sys.executable).resolve().parent
else:
    # 開發模式方便手動測試合併邏輯，但因為 dist 檔案不存在，self_relocate 仍會中止
    SRC_ROOT = Path(__file__).resolve().parent.parent

DEST = Path(os.environ["LOCALAPPDATA"]) / "TerminalPet"
PET_EXE = DEST / "TerminalPet.exe"
STATE_EXE = DEST / "state" / "PetState.exe"
STATE_DIR = Path.home() / ".terminalpet"
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
STARTUP_DIR = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
STARTUP_LNK = STARTUP_DIR / "TerminalPet.lnk"

REQUIRED_ITEMS = ["TerminalPet.exe", "_internal", "state"]

# ---- hook 事件 <-> 狀態對應 ----
EVENT_STATE_MAP = {
    "PreToolUse": "working",
    "UserPromptSubmit": "thinking",
    "Notification": "waiting",
    "Stop": "done",
    "SessionEnd": "sleeping",
}

_FINGERPRINT_RE = re.compile(
    r'petstate\.exe"?\s+(' + "|".join(EVENT_STATE_MAP.values()) + r")\s*$",
    re.IGNORECASE,
)


def is_our_hook(command) -> bool:
    """判斷一個 hook 的 command 字串是否是我們自己裝的（PetState.exe + 合法狀態名結尾）。"""
    return isinstance(command, str) and bool(_FINGERPRINT_RE.search(command))


# ---- settings.json 讀寫 ----
def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        backup = path.with_name(f"settings.json.broken-{int(time.time())}.bak")
        shutil.copy2(path, backup)
        print(f"錯誤：{path} 目前不是合法的 JSON，已備份到：{backup}")
        print("為了不弄丟你原本的設定，安裝程式不會嘗試自動修復或覆蓋它。")
        print("請手動修好這個檔案後，重新執行安裝程式。")
        input("按 Enter 鍵結束...")
        sys.exit(1)


def backup_and_write(path: Path, data: dict) -> None:
    if path.exists():
        shutil.copy2(path, path.with_name("settings.json.bak"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def find_our_group(groups: list):
    """在事件的 group 陣列中，找出『沒有 matcher（套用到全部）』的那一組。"""
    for g in groups:
        if not isinstance(g, dict):
            continue
        matcher = g.get("matcher")
        if not matcher or matcher == "*":
            return g
    return None


def merge_event(hooks_dict: dict, event: str, command: str) -> str | None:
    """把一條 hook 合併進 hooks_dict[event]，回傳警告訊息（沒有警告則回傳 None）。"""
    groups = hooks_dict.setdefault(event, [])
    if not isinstance(groups, list):
        return f"警告：settings.json 的 hooks.{event} 格式異常（不是陣列），已略過此事件，其餘事件正常處理。"

    group = find_our_group(groups)
    if group is None:
        group = {"hooks": []}
        groups.append(group)

    inner = group.setdefault("hooks", [])
    if not isinstance(inner, list):
        return f"警告：settings.json 的 hooks.{event} 內有一組格式異常（hooks 不是陣列），已略過此事件。"

    our_obj = {"type": "command", "command": command, "shell": "bash", "async": True}
    for i, h in enumerate(inner):
        if isinstance(h, dict) and is_our_hook(h.get("command")):
            inner[i] = our_obj
            return None
    inner.append(our_obj)
    return None


def unmerge_event(hooks_dict: dict, event: str) -> None:
    """從 hooks_dict[event] 移除我們自己加的那一條，並清理因此變空的容器。"""
    groups = hooks_dict.get(event)
    if not isinstance(groups, list):
        return
    group = find_our_group(groups)
    if group is None:
        return
    inner = group.get("hooks")
    if not isinstance(inner, list):
        return
    inner[:] = [h for h in inner if not (isinstance(h, dict) and is_our_hook(h.get("command")))]
    if not inner:
        groups.remove(group)
    if not groups:
        del hooks_dict[event]


def merge_settings() -> tuple[list[str], dict]:
    data = load_settings(SETTINGS_PATH)
    warnings = []

    hooks_dict = data.get("hooks")
    if not isinstance(hooks_dict, dict):
        if "hooks" in data:
            warnings.append("警告：settings.json 的 hooks 欄位格式異常，已重建為空白（其餘設定不受影響）。")
        hooks_dict = {}
        data["hooks"] = hooks_dict

    state_exe_str = str(STATE_EXE).replace("\\", "/")
    for event, state in EVENT_STATE_MAP.items():
        command = f'"{state_exe_str}" {state}'
        warn = merge_event(hooks_dict, event, command)
        if warn:
            warnings.append(warn)

    backup_and_write(SETTINGS_PATH, data)
    return warnings, data


def remove_hooks() -> bool:
    """回傳是否有實際變更。"""
    data = load_settings(SETTINGS_PATH)
    hooks_dict = data.get("hooks")
    if not isinstance(hooks_dict, dict):
        return False

    before = json.dumps(hooks_dict, sort_keys=True)
    for event in list(EVENT_STATE_MAP):
        unmerge_event(hooks_dict, event)
    if not hooks_dict:
        data.pop("hooks", None)
    after = json.dumps(data.get("hooks", {}), sort_keys=True)

    if before == after:
        return False
    backup_and_write(SETTINGS_PATH, data)
    return True


# ---- 自我搬遷 ----
def self_relocate() -> None:
    missing = [name for name in REQUIRED_ITEMS if not (SRC_ROOT / name).exists()]
    if missing:
        print(f"錯誤：在 {SRC_ROOT} 找不到必要檔案 {missing}。")
        print("請確認 Setup-TerminalPet.exe 跟 TerminalPet.exe、state 等檔案放在同一個資料夾內，不要單獨移出來執行。")
        input("按 Enter 鍵結束...")
        sys.exit(1)

    try:
        shutil.copytree(
            SRC_ROOT,
            DEST,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("Setup-TerminalPet.exe", "使用說明.txt"),
        )
    except PermissionError:
        print("偵測到 TerminalPet 可能正在執行中，複製檔案失敗。")
        print("請先在桌寵上按右鍵選擇「關閉桌寵」，再重新執行安裝程式。")
        input("按 Enter 鍵結束...")
        sys.exit(1)


# ---- 開機自動啟動 ----
def setup_autostart(theme: str) -> None:
    args = "" if theme == "animal" else "light"
    ps_script = (
        "$WshShell = New-Object -ComObject WScript.Shell\n"
        f'$Shortcut = $WshShell.CreateShortcut("{STARTUP_LNK}")\n'
        f'$Shortcut.TargetPath = "{PET_EXE}"\n'
        f'$Shortcut.Arguments = "{args}"\n'
        f'$Shortcut.WorkingDirectory = "{PET_EXE.parent}"\n'
        "$Shortcut.Save()\n"
    )
    STARTUP_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
        check=True,
        capture_output=True,
    )


def remove_autostart() -> None:
    if STARTUP_LNK.exists():
        STARTUP_LNK.unlink()


# ---- 互動小工具 ----
def ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    ans = input(f"{prompt} {suffix}: ").strip().lower()
    if not ans:
        return default
    return ans in ("y", "yes", "是")


def ask_theme() -> str:
    print("要用哪個外觀？")
    print("  1) 動物版（預設，原創小狼像素圖）")
    print("  2) 紅綠燈版（低調小圓點，適合辦公室）")
    choice = input("請選擇 [1/2，直接按 Enter＝1]: ").strip()
    return "light" if choice == "2" else "animal"


# ---- 主流程 ----
def do_install() -> None:
    print("開始安裝 TerminalPet...")
    self_relocate()
    print(f"已將程式安裝到：{DEST}")

    theme = ask_theme()
    autostart = ask_yes_no("是否要設定「開機自動啟動桌寵」？", default=True)

    warnings, _ = merge_settings()
    for w in warnings:
        print(w)
    print("已將桌寵狀態 hook 寫入 Claude Code 設定（不影響你原本的其他設定）。")

    if autostart:
        try:
            setup_autostart(theme)
            print("已設定開機自動啟動。")
        except subprocess.CalledProcessError:
            print("警告：開機自動啟動捷徑建立失敗，可略過此步驟，不影響桌寵本身運作。")

    print()
    print("安裝完成！")
    theme_args = [] if theme == "animal" else ["light"]
    try:
        subprocess.Popen([str(PET_EXE), *theme_args])
    except OSError:
        pass
    input("按 Enter 鍵結束...")


def do_uninstall() -> None:
    print("開始解除安裝 TerminalPet...")

    if remove_hooks():
        print("已從 settings.json 移除 TerminalPet 的 hook 設定（其餘設定保持原樣）。")
    else:
        print("settings.json 中沒有找到 TerminalPet 的 hook 設定，略過。")

    remove_autostart()
    print("已移除開機自動啟動捷徑（如果原本有的話）。")

    if DEST.exists() and ask_yes_no(f"是否要刪除安裝資料夾 {DEST}？", default=True):
        shutil.rmtree(DEST, ignore_errors=True)
        print("已刪除安裝資料夾。")

    if STATE_DIR.exists() and ask_yes_no(f"是否要一併刪除狀態檔資料夾 {STATE_DIR}？", default=False):
        shutil.rmtree(STATE_DIR, ignore_errors=True)
        print("已刪除狀態檔資料夾。")

    print()
    print("解除安裝完成。")
    input("按 Enter 鍵結束...")


def main() -> None:
    print("=" * 40)
    print("TerminalPet 安裝程式")
    print("=" * 40)

    if DEST.exists():
        print(f"偵測到 TerminalPet 已安裝於：{DEST}")
        print("  1) 更新／重新安裝")
        print("  2) 解除安裝")
        print("  3) 取消")
        choice = input("請選擇 [1/2/3]: ").strip()
        if choice == "2":
            do_uninstall()
            return
        if choice == "3":
            print("已取消。")
            return

    do_install()


if __name__ == "__main__":
    main()
