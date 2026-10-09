"""set_state.py 的測試（案例見 tests/cases/手動測試工具.md，條文見 docs/specs/SPEC.md TOOL 模組）。

以模擬指令列的方式呼叫 main()；session 資料夾一律換成暫存資料夾，不碰 ~/.terminalpet/。
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pet  # noqa: E402
import set_state  # noqa: E402


@pytest.fixture
def sessions_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(set_state, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(pet, "SESSIONS_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def run(monkeypatch):
    """模擬在終端機執行 `python set_state.py <args>`；at 指定當下時間。"""
    def _run(*args: str, at: float = 1000.0):
        monkeypatch.setattr(set_state.time, "time", lambda: at)
        monkeypatch.setattr(sys, "argv", ["set_state.py", *args])
        set_state.main()
    return _run


def read(directory: Path, sid: str) -> dict:
    return json.loads((directory / f"{sid}.json").read_text(encoding="utf-8"))


def test_T01_AC_TOOL_01_default_manual_session(sessions_dir, run):
    run("waiting")

    data = read(sessions_dir, "manual")
    assert data["state"] == "waiting"
    assert data["project"] == "manual"


def test_T02_AC_TOOL_02_custom_name_gets_prefix(sessions_dir, run):
    run("working", "--session", "b", "--project", "另一個專案")

    data = read(sessions_dir, "manual-b")
    assert data["state"] == "working"
    assert data["project"] == "另一個專案"
    assert not (sessions_dir / "b.json").exists()


def test_T03_AC_TOOL_02_manual_prefixed_name_kept(sessions_dir, run):
    run("idle", "--session", "manual2")

    assert (sessions_dir / "manual2.json").exists()
    assert not (sessions_dir / "manual-manual2.json").exists()


def test_T04_AC_TOOL_03_state_change_keeps_project_and_start(sessions_dir, run):
    run("working", "--session", "b", "--project", "另一個專案", at=100.0)
    run("done", "--session", "b", at=200.0)

    data = read(sessions_dir, "manual-b")
    assert data["state"] == "done"
    assert data["project"] == "另一個專案"
    assert data["start"] == 100.0
    assert data["since"] == 200.0


def test_T05_AC_TOOL_03_same_state_keeps_since(sessions_dir, run):
    run("working", at=100.0)
    run("working", at=160.0)

    data = read(sessions_dir, "manual")
    assert data["ts"] == 160.0
    assert data["since"] == 100.0


def test_T06_AC_TOOL_04_end_removes_session(sessions_dir, run):
    run("working", "--session", "b")
    run("end", "--session", "b")

    assert not (sessions_dir / "manual-b.json").exists()


def test_T07_AC_TOOL_05_unknown_state_rejected(sessions_dir, run):
    with pytest.raises(ValueError) as exc:
        run("foo")

    for state in set_state.VALID_STATES:
        assert state in str(exc.value)
    assert list(sessions_dir.iterdir()) == []


def test_T08_AC_TOOL_06_clear_only_removes_fake_sessions(sessions_dir, run):
    run("waiting")
    run("working", "--session", "b")
    real = sessions_dir / "abc123.json"
    real.write_text('{"state":"working","ts":1000}', encoding="utf-8")

    run("clear")

    assert sorted(p.name for p in sessions_dir.iterdir()) == ["abc123.json"]


def test_T09_AC_TOOL_07_clear_without_fake_sessions(sessions_dir, run):
    real = sessions_dir / "abc123.json"
    content = '{"state":"working","ts":1000}'
    real.write_text(content, encoding="utf-8")

    run("clear")

    assert real.read_text(encoding="utf-8") == content


def test_T10_AC_TOOL_01_written_file_readable_by_pet(sessions_dir, run):
    run("done", "--session", "b", "--project", "Blog", at=1000.0)

    result = pet.load_sessions(now=1001.0)

    assert [(s.label, s.state) for s in result] == [("Blog", "done")]


def test_T11_AC_HOOK_16_set_state_writes_empty_transcript(sessions_dir, run):
    run("waiting")

    assert read(sessions_dir, "manual")["transcript"] == ""
