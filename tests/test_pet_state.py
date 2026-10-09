"""scripts/pet-state.sh 與 hook 事件對應的測試（案例見 tests/cases/狀態寫入.md，條文見 docs/specs/SPEC.md HOOK 模組）。

腳本以 bash 實際執行，HOME 指向暫存資料夾，不碰 ~/.terminalpet/。
Windows 上指定 Git Bash，避免 PATH 裡的 WSL bash；找不到可用的 bash 就略過。
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import install  # noqa: E402
import pet  # noqa: E402

SCRIPT = ROOT / "scripts" / "pet-state.sh"

# SPEC.md HOOK 模組的事件對應表
SPEC_EVENT_STATE = {
    "SessionStart": "idle",
    "UserPromptSubmit": "thinking",
    "PreToolUse": "working",
    "PostToolUse": "working",
    "PermissionRequest": "waiting",
    "Notification": "waiting",
    "Stop": "done",
    "SessionEnd": "end",
}
SPEC_NOTIFICATION_TYPES = {"permission_prompt", "elicitation_dialog", "agent_needs_input"}


def find_bash() -> str | None:
    if sys.platform == "win32":
        for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
            if Path(candidate).exists():
                return candidate
        found = shutil.which("bash")
        # WindowsApps／System32 底下的 bash 是 WSL，不是 Git Bash
        if found and "windowsapps" not in found.lower() and "system32" not in found.lower():
            return found
        return None
    return shutil.which("bash")


BASH = find_bash()
needs_bash = pytest.mark.skipif(BASH is None, reason="找不到 Git Bash／bash")


@pytest.fixture
def home(tmp_path):
    return tmp_path


def sessions(home: Path) -> Path:
    return home / ".terminalpet" / "sessions"


def run_hook(home: Path, *args: str, payload: dict | None = None) -> subprocess.CompletedProcess:
    """模擬 Claude Code 呼叫 hook：payload 轉成 JSON 從 stdin 餵進去。"""
    env = dict(os.environ, HOME=str(home))
    stdin = "" if payload is None else json.dumps(payload)
    result = subprocess.run([BASH, SCRIPT.as_posix(), *args], input=stdin, text=True,
                            capture_output=True, env=env, timeout=10)
    assert result.returncode == 0, result.stderr  # 全域規則：不拖累 Claude Code
    return result


def read(home: Path, sid: str) -> dict:
    return json.loads((sessions(home) / f"{sid}.json").read_text(encoding="utf-8"))


def write_existing(home: Path, sid: str, **fields) -> Path:
    sessions(home).mkdir(parents=True, exist_ok=True)
    path = sessions(home) / f"{sid}.json"
    path.write_text(json.dumps({"sid": sid, "project": "p", "cwd": "", **fields},
                               separators=(",", ":")), encoding="utf-8")
    return path


@needs_bash
def test_T01_AC_HOOK_01_session_start_creates_idle(home):
    run_hook(home, "idle", payload={"session_id": "abc123"})

    assert read(home, "abc123")["state"] == "idle"


@needs_bash
@pytest.mark.parametrize("tool, expected", [
    ("AskUserQuestion", "waiting"), ("ExitPlanMode", "waiting"), ("Bash", "working"),
])
def test_T02_AC_HOOK_02_asking_tools_become_waiting(home, tool, expected):
    run_hook(home, "working", payload={"session_id": "abc123", "tool_name": tool})

    assert read(home, "abc123")["state"] == expected


@needs_bash
@pytest.mark.parametrize("command", ["end", "sleeping"])
def test_T03_AC_HOOK_03_05_end_and_sleeping_delete(home, command):
    run_hook(home, "working", payload={"session_id": "abc123"})
    run_hook(home, command, payload={"session_id": "abc123"})

    assert not (sessions(home) / "abc123.json").exists()


@needs_bash
def test_T04_AC_HOOK_06_no_state_argument_writes_nothing(home):
    run_hook(home, payload={"session_id": "abc123"})

    assert not sessions(home).exists() or list(sessions(home).iterdir()) == []


@needs_bash
def test_T05_AC_HOOK_07_unknown_state_written_as_is(home):
    run_hook(home, "workng", payload={"session_id": "abc123"})

    assert read(home, "abc123")["state"] == "workng"


@needs_bash
def test_T06_AC_HOOK_08_empty_stdin_uses_default(home):
    run_hook(home, "working")

    assert read(home, "default")["state"] == "working"


@needs_bash
def test_T07_AC_HOOK_09_project_and_cwd_normalized(home):
    run_hook(home, "working", payload={"session_id": "abc123", "cwd": "D:\\Projects\\TerminalPet\\"})

    data = read(home, "abc123")
    assert data["project"] == "TerminalPet"
    assert data["cwd"] == "D:/Projects/TerminalPet"


@needs_bash
def test_T08_AC_HOOK_10_no_cwd_uses_sid_as_project(home):
    run_hook(home, "working", payload={"session_id": "abc123"})

    data = read(home, "abc123")
    assert data["project"] == "abc123"
    assert data["cwd"] == ""


@needs_bash
def test_T09_AC_HOOK_11_no_session_id_uses_default(home):
    run_hook(home, "working", payload={"cwd": "D:\\Projects\\Blog"})

    assert sorted(p.name for p in sessions(home).iterdir()) == ["default.json"]


@needs_bash
def test_T10_AC_HOOK_12_session_id_sanitized(home):
    run_hook(home, "working", payload={"session_id": "a/b:c"})

    assert sorted(p.name for p in sessions(home).iterdir()) == ["abc.json"]


@needs_bash
def test_T11_AC_HOOK_13_since_kept_until_state_changes(home):
    write_existing(home, "abc123", state="working", ts=100.0, since=100.0, start=100.0)

    run_hook(home, "working", payload={"session_id": "abc123"})
    after_working = read(home, "abc123")
    run_hook(home, "done", payload={"session_id": "abc123"})
    after_done = read(home, "abc123")

    assert after_working["since"] == 100.0
    assert after_working["ts"] > 100.0
    assert after_done["state"] == "done"
    assert after_done["since"] == after_done["ts"]
    assert after_working["start"] == after_done["start"] == 100.0


@needs_bash
def test_T12_AC_HOOK_14_older_event_discarded(home):
    path = write_existing(home, "abc123", state="waiting", ts=9999999999.5,
                          since=9999999999.5, start=100.0)
    before = path.read_text(encoding="utf-8")

    run_hook(home, "working", payload={"session_id": "abc123"})

    assert path.read_text(encoding="utf-8") == before


def test_T13_event_mapping_matches_spec():
    plugin = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]

    assert install.EVENT_STATE == SPEC_EVENT_STATE
    assert set(install.EVENT_MATCHER) == {"Notification"}
    assert set(install.EVENT_MATCHER["Notification"].split("|")) == SPEC_NOTIFICATION_TYPES

    assert set(plugin) == set(SPEC_EVENT_STATE)
    for event, state in SPEC_EVENT_STATE.items():
        groups = plugin[event]
        assert len(groups) == 1
        hook = groups[0]["hooks"][0]
        assert hook["command"].endswith(f"pet-state.sh\" {state}")
        assert hook["async"] is True
        if event == "Notification":
            assert set(groups[0]["matcher"].split("|")) == SPEC_NOTIFICATION_TYPES
        else:
            assert "matcher" not in groups[0]


@needs_bash
def test_T14_AC_HOOK_01_written_file_readable_by_pet(home, monkeypatch):
    run_hook(home, "waiting", payload={"session_id": "abc123", "cwd": "D:\\Projects\\Blog"})
    monkeypatch.setattr(pet, "SESSIONS_DIR", sessions(home))

    result = pet.load_sessions()

    assert [(s.label, s.state) for s in result] == [("Blog", "waiting")]
