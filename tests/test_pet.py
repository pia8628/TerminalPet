"""pet.py 狀態判定的測試（案例見 tests/cases/狀態判定.md，條文見 docs/specs/SPEC.md SESS 模組）。

只測不依賴視窗的狀態讀取函式；session 資料夾一律換成暫存資料夾，不碰 ~/.terminalpet/。
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pet  # noqa: E402
from pet import Session, aggregate_state, effective_state, format_elapsed, load_sessions  # noqa: E402

NOW = 1_000_000.0  # 固定的「現在」，結果不受執行時刻影響


@pytest.fixture
def sessions_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(pet, "SESSIONS_DIR", tmp_path)
    return tmp_path


def write_session(directory: Path, sid: str, state: str, age: float = 0,
                  start: float | None = None, project: str | None = "proj") -> Path:
    """寫一個 session 檔；age = 距離 NOW 的秒數（最後更新時間 = NOW - age）。"""
    ts = NOW - age
    data = {"state": state, "ts": ts, "since": ts, "start": ts if start is None else start,
            "sid": sid, "cwd": ""}
    if project is not None:
        data["project"] = project
    path = directory / f"{sid}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def make_session(state: str) -> Session:
    return Session(sid=state, state=state, project="p", cwd="", since=0, ts=0, start=0)


# ---- 逾時轉灰 ----

@pytest.mark.parametrize("age, expected", [(600, "working"), (601, "idle")])
def test_T01_AC_SESS_01_02_working_turns_idle_after_600s(age, expected):
    assert effective_state("working", age) == expected


@pytest.mark.parametrize("age, expected", [(600, "thinking"), (601, "idle")])
def test_T02_AC_SESS_01_thinking_turns_idle_after_600s(age, expected):
    assert effective_state("thinking", age) == expected


@pytest.mark.parametrize("age, expected", [(1800, "done"), (1801, "idle")])
def test_T03_AC_SESS_03_done_turns_idle_after_1800s(age, expected):
    assert effective_state("done", age) == expected


def test_T04_AC_SESS_04_waiting_never_turns_idle():
    assert effective_state("waiting", 18000) == "waiting"


@pytest.mark.parametrize("raw", ["workng", "sleeping"])
def test_T05_AC_HOOK_07_unknown_state_is_idle(raw):
    assert effective_state(raw, 0) == "idle"


# ---- 過期刪檔 ----

def test_T06_AC_SESS_05_non_waiting_removed_after_10800s(sessions_dir):
    kept = write_session(sessions_dir, "kept", "working", age=10800)
    gone = write_session(sessions_dir, "gone", "working", age=10801)

    result = load_sessions(NOW)

    assert [(s.sid, s.state) for s in result] == [("kept", "idle")]
    assert kept.exists()
    assert not gone.exists()


def test_T07_AC_SESS_06_waiting_removed_after_43200s(sessions_dir):
    kept = write_session(sessions_dir, "kept", "waiting", age=43200)
    gone = write_session(sessions_dir, "gone", "waiting", age=43201)

    result = load_sessions(NOW)

    assert [(s.sid, s.state) for s in result] == [("kept", "waiting")]
    assert kept.exists()
    assert not gone.exists()


# ---- 壞檔處理 ----

def test_T08_AC_SESS_07_partial_file_uses_cached_content(sessions_dir):
    path = write_session(sessions_dir, "abc123", "working")
    cache = {}
    load_sessions(NOW, cache)

    path.write_text('{"state":"wor', encoding="utf-8")  # 模擬寫到一半
    result = load_sessions(NOW, cache)

    assert [(s.sid, s.state) for s in result] == [("abc123", "working")]
    assert path.exists()


def test_T09_AC_SESS_08_never_parsed_bad_files_are_skipped(sessions_dir):
    bad = sessions_dir / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    bad2 = sessions_dir / "bad2.json"
    bad2.write_text(json.dumps({"state": "working", "ts": "abc"}), encoding="utf-8")
    write_session(sessions_dir, "ok", "working")

    result = load_sessions(NOW)

    assert [s.sid for s in result] == ["ok"]
    assert bad.exists()
    assert bad2.exists()


# ---- 排序與名稱 ----

def test_T10_AC_SESS_09_sorted_by_start_then_sid(sessions_dir):
    for sid, start in (("C", 300), ("Y", 400), ("A", 200), ("X", 400), ("B", 100)):
        write_session(sessions_dir, sid, "working", start=NOW - 1000 + start)

    result = load_sessions(NOW)

    assert [s.sid for s in result] == ["B", "A", "C", "X", "Y"]


def test_T11_AC_SESS_10_same_project_numbered(sessions_dir):
    write_session(sessions_dir, "s2", "working", start=NOW - 800, project="TerminalPet")
    write_session(sessions_dir, "s1", "working", start=NOW - 900, project="TerminalPet")
    write_session(sessions_dir, "s3", "working", start=NOW - 700, project="Blog")

    result = load_sessions(NOW)

    assert [s.label for s in result] == ["TerminalPet #1", "TerminalPet #2", "Blog"]


def test_T12_AC_SESS_11_missing_project_uses_sid_prefix(sessions_dir):
    write_session(sessions_dir, "0123456789abcdef", "working", project=None)

    result = load_sessions(NOW)

    assert [s.label for s in result] == ["01234567"]


# ---- 整體狀態 ----

def test_T13_AC_SESS_12_aggregate_picks_most_urgent():
    sessions = [make_session(s) for s in ("working", "done", "thinking")]
    assert aggregate_state(sessions) == "done"
    assert aggregate_state(sessions + [make_session("waiting")]) == "waiting"


def test_T14_AC_SESS_13_aggregate_of_nothing_is_idle():
    assert aggregate_state([]) == "idle"


# ---- 經過時間文字 ----

@pytest.mark.parametrize("seconds, expected", [
    (0, "剛剛"), (59, "剛剛"), (60, "1 分"), (3599, "59 分"),
    (3600, "1 小時 0 分"), (3725, "1 小時 2 分"), (-5, "剛剛"),
])
def test_T15_AC_VIEW_08_format_elapsed(seconds, expected):
    assert format_elapsed(seconds) == expected
