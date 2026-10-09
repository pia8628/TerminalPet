"""pet.py 狀態判定的測試（案例見 tests/cases/狀態判定.md，條文見 docs/specs/SPEC.md SESS 模組）。

另含右鍵選單「切換到終端機」與背景跳轉的測試（條文見 docs/specs/changes/click-to-terminal/delta.md）。
狀態讀取函式不依賴視窗；session 資料夾一律換成暫存資料夾，不碰 ~/.terminalpet/。
"""

import json
import os
import sys
import threading
import time
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


# ---- 對話紀錄檔路徑（點擊跳到終端機用） ----

def test_session_reads_transcript_path(sessions_dir):
    path = write_session(sessions_dir, "abc123", "working")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["transcript"] = "C:/Users/me/.claude/projects/p/abc123.jsonl"
    path.write_text(json.dumps(data), encoding="utf-8")
    write_session(sessions_dir, "old", "working")  # 舊版狀態檔沒有這個欄位

    result = {s.sid: s.transcript for s in load_sessions(NOW)}

    assert result == {"abc123": "C:/Users/me/.claude/projects/p/abc123.jsonl", "old": ""}


# ======================================================================
# 右鍵選單與背景跳轉（需要 Qt；用 offscreen 平台，不會真的顯示視窗）
# ======================================================================

@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pet_window(qapp, sessions_dir, monkeypatch):
    monkeypatch.setattr(pet, "CONFIG_FILE", sessions_dir / "config.json")  # 不碰真正的設定檔
    windows = []

    def make(*sessions):
        now = time.time()
        for sid, cwd, transcript in sessions:
            data = {"state": "working", "ts": now, "since": now, "start": now, "sid": sid,
                    "project": sid, "cwd": cwd, "transcript": transcript}
            (sessions_dir / f"{sid}.json").write_text(json.dumps(data), encoding="utf-8")
        w = pet.PetWindow(dict(pet.DEFAULT_CONFIG))
        windows.append(w)
        return w

    yield make
    for w in windows:
        w.timer.stop()
        w.deleteLater()


def submenus(w) -> tuple:
    from PySide6.QtWidgets import QMenu
    menu = QMenu()
    w._populate_menu(menu)
    return {a.text().split()[0]: a.menu() for a in menu.actions() if a.menu()}, menu


def test_AC_OPS_05_session_submenu_order(pet_window, monkeypatch):
    monkeypatch.setattr(pet.wt_jump, "supported", lambda: True)
    w = pet_window(("with-cwd", "D:/Projects/A", "a.jsonl"), ("no-cwd", "", ""))

    subs, _menu = submenus(w)

    assert [a.text() for a in subs["with-cwd"].actions()] == ["切換到終端機", "開啟資料夾", "從清單移除"]
    assert [a.text() for a in subs["no-cwd"].actions()] == ["切換到終端機", "從清單移除"]


def test_AC_JUMP_08_no_switch_item_on_non_windows(pet_window, monkeypatch):
    monkeypatch.setattr(pet.wt_jump, "supported", lambda: False)
    w = pet_window(("with-cwd", "D:/Projects/A", "a.jsonl"))

    subs, _menu = submenus(w)

    assert [a.text() for a in subs["with-cwd"].actions()] == ["開啟資料夾", "從清單移除"]


def test_AC_JUMP_03_switch_item_jumps_with_that_sessions_transcript(pet_window, monkeypatch):
    monkeypatch.setattr(pet.wt_jump, "supported", lambda: True)
    w = pet_window(("s1", "", "C:/t/s1.jsonl"), ("s2", "", "C:/t/s2.jsonl"))
    started = []
    monkeypatch.setattr(w._jumper, "start", started.append)

    subs, _menu = submenus(w)
    subs["s2"].actions()[0].trigger()

    assert started == ["C:/t/s2.jsonl"]


def wait_for(qapp, predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.005)


def test_jump_runs_in_background_and_result_returns_on_main_thread(qapp):
    from PySide6.QtCore import QTimer
    main = threading.get_ident()
    job_threads, received, ticks = [], [], []

    def slow_job(transcript, cancelled):
        job_threads.append(threading.get_ident())
        time.sleep(0.3)  # 模擬讀檔＋UI Automation 花的時間
        return pet.wt_jump.JumpResult(pet.wt_jump.OK, 1)

    runner = pet.JumpRunner(job=slow_job)
    runner.finished.connect(lambda r: received.append((r, threading.get_ident())))
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(10)

    t0 = time.monotonic()
    runner.start("C:/t/s1.jsonl")
    start_cost = time.monotonic() - t0
    wait_for(qapp, lambda: received)
    timer.stop()

    assert start_cost < 0.1  # start() 立刻返回，不等跳轉做完
    assert job_threads and job_threads[0] != main
    assert received == [(pet.wt_jump.JumpResult(pet.wt_jump.OK, 1), main)]
    assert len(ticks) >= 5  # 背景處理期間主執行緒的計時器照常在跑（燈號、閃燈不受影響）


def test_jump_errors_are_reported_not_raised(qapp):
    received = []

    def broken_job(transcript, cancelled):
        raise RuntimeError("壞掉")

    runner = pet.JumpRunner(job=broken_job)
    runner.finished.connect(received.append)
    runner.start("")
    wait_for(qapp, lambda: received)

    assert [r.code for r in received] == [pet.wt_jump.FAILED]


# ---- 跳不過去時的提示與保護（04 卡） ----

R = pet.wt_jump.JumpResult


@pytest.mark.parametrize("result, expected", [
    (R(pet.wt_jump.AMBIGUOUS, 2), "有 2 個分頁同名，請手動切換"),
    (R(pet.wt_jump.AMBIGUOUS, 3), "有 3 個分頁同名，請手動切換"),
    (R(pet.wt_jump.NO_TITLE), "找不到這個 session 的分頁"),
    (R(pet.wt_jump.NO_WINDOW), "找不到這個 session 的分頁"),
    (R(pet.wt_jump.NO_MATCH), "找不到這個 session 的分頁"),
    (R(pet.wt_jump.FAILED, 1), "切換失敗，請手動切換"),
    (R(pet.wt_jump.FAILED), "切換失敗，請手動切換"),
    (R(pet.wt_jump.OK, 1), None),
    (R(pet.wt_jump.UNSUPPORTED), None),  # AC-JUMP-08：非 Windows 不出提示
])
def test_AC_JUMP_13_to_19_hint_text(result, expected):
    assert pet.jump_hint_text(result) == expected


def gated_job(results, gate):
    """假的跳轉：等 gate 打開才回傳 results 裡的下一個結果，並記下被呼叫的紀錄檔。"""
    calls = []

    def job(transcript, cancelled):
        calls.append(transcript)
        gate.wait(5)
        return results.pop(0)

    return job, calls


def test_AC_JUMP_20_second_jump_while_busy_is_ignored(pet_window, qapp):
    w = pet_window(("s1", "", "C:/t/s1.jsonl"), ("s2", "", "C:/t/s2.jsonl"))
    gate = threading.Event()
    job, calls = gated_job([R(pet.wt_jump.OK, 1)], gate)
    w._jumper._job = job
    received = []
    w._jumper.finished.connect(received.append)

    w._jump_to("C:/t/s1.jsonl")
    w._jump_to("C:/t/s2.jsonl")  # 第一個還在處理中
    gate.set()
    wait_for(qapp, lambda: received)
    wait_for(qapp, lambda: False, timeout=0.1)

    assert calls == ["C:/t/s1.jsonl"]  # 第二次沒有開始
    assert received == [R(pet.wt_jump.OK, 1)]  # 第一個照常完成
    assert not w._hint.isVisible()  # 被忽略的那次不出提示，成功也不出提示

    # 處理完之後可以再跳
    gate.clear()
    job2, calls2 = gated_job([R(pet.wt_jump.OK, 1)], gate)
    w._jumper._job = job2
    gate.set()
    w._jump_to("C:/t/s2.jsonl")
    wait_for(qapp, lambda: len(received) == 2)
    assert calls2 == ["C:/t/s2.jsonl"]


def test_AC_JUMP_19_timeout_reports_failed_once_and_cancels_worker(qapp):
    gate = threading.Event()
    seen_cancel = []

    def stuck_job(transcript, cancelled):
        gate.wait(5)  # 模擬卡住的系統呼叫
        seen_cancel.append(cancelled())
        return R(pet.wt_jump.OK, 1)  # 逾時之後才晚到的結果

    runner = pet.JumpRunner(job=stuck_job, timeout_ms=100)
    received = []
    runner.finished.connect(received.append)
    runner.start("C:/t/s1.jsonl")
    wait_for(qapp, lambda: received)

    assert received == [R(pet.wt_jump.FAILED)]  # 逾時 → 切換失敗
    assert not runner.busy

    gate.set()
    wait_for(qapp, lambda: seen_cancel)
    wait_for(qapp, lambda: False, timeout=0.2)  # 讓晚到的結果有機會送回主執行緒

    assert seen_cancel == [True]  # worker 看得到取消旗標，不會再開始新的切換動作
    assert received == [R(pet.wt_jump.FAILED)]  # 晚到的結果被丟掉，沒有第二個提示


def test_AC_JUMP_19_late_result_of_old_jump_does_not_leak_into_new_jump(qapp):
    old_gate, new_gate = threading.Event(), threading.Event()
    gates = [old_gate, new_gate]
    results = [R(pet.wt_jump.OK, 1), R(pet.wt_jump.NO_MATCH)]

    def job(transcript, cancelled):
        gates.pop(0).wait(5)
        return results.pop(0)

    runner = pet.JumpRunner(job=job, timeout_ms=100)
    received = []
    runner.finished.connect(received.append)
    runner.start("old")
    wait_for(qapp, lambda: received)  # 第一個逾時
    runner._timeout_ms = 3000
    runner.start("new")
    old_gate.set()  # 第一個的結果在第二個處理中晚到
    wait_for(qapp, lambda: False, timeout=0.2)

    assert received == [R(pet.wt_jump.FAILED)]  # 世代編號不符：沒有被當成第二個跳轉的結果
    assert runner.busy

    new_gate.set()
    wait_for(qapp, lambda: len(received) == 2)
    assert received == [R(pet.wt_jump.FAILED), R(pet.wt_jump.NO_MATCH)]


def test_closing_pet_sets_cancel_flag(pet_window, qapp):
    w = pet_window(("s1", "", "C:/t/s1.jsonl"))
    gate = threading.Event()
    seen_cancel = []

    def job(transcript, cancelled):
        gate.wait(5)
        seen_cancel.append(cancelled())
        return R(pet.wt_jump.OK, 1)

    w._jumper._job = job
    received = []
    w._jumper.finished.connect(received.append)
    w._jump_to("C:/t/s1.jsonl")
    qapp.aboutToQuit.emit()  # 等同按「關閉桌寵」時 Qt 發出的通知
    gate.set()
    wait_for(qapp, lambda: seen_cancel)
    wait_for(qapp, lambda: False, timeout=0.1)

    assert seen_cancel == [True]
    assert received == []  # 關閉時不再回報、不出提示


@pytest.mark.parametrize("result, text", [
    (R(pet.wt_jump.NO_MATCH), "找不到這個 session 的分頁"),
    (R(pet.wt_jump.AMBIGUOUS, 2), "有 2 個分頁同名，請手動切換"),
    (R(pet.wt_jump.FAILED, 1), "切換失敗，請手動切換"),
])
def test_AC_JUMP_13_to_19_hint_is_shown_after_failed_jump(pet_window, qapp, result, text):
    w = pet_window(("s1", "", "C:/t/s1.jsonl"))
    w.show()
    w._jumper._job = lambda transcript, cancelled: result
    w._jump_to("C:/t/s1.jsonl")
    wait_for(qapp, lambda: w._hint.isVisible())

    assert w._hint.isVisible()
    assert w._hint.text() == text
    w.hide()


def test_AC_JUMP_08_no_hint_on_success_or_unsupported(pet_window, qapp):
    w = pet_window(("s1", "", "C:/t/s1.jsonl"))
    w.show()
    for result in (R(pet.wt_jump.OK, 1), R(pet.wt_jump.UNSUPPORTED)):
        w._on_jump_finished(result)
        assert not w._hint.isVisible()
    w.hide()


def test_AC_JUMP_18_hint_disappears_by_itself_and_does_not_block_pet(pet_window, qapp, monkeypatch):
    from PySide6.QtCore import Qt
    monkeypatch.setattr(pet, "HINT_MS", 150)
    w = pet_window(("s1", "", "C:/t/s1.jsonl"))
    w.show()
    w._on_jump_finished(R(pet.wt_jump.NO_MATCH))

    assert w._hint.isVisible()
    # 不接收滑鼠、不搶焦點：桌寵的拖曳、右鍵、點擊照常，剛叫到前面的 WT 不會被搶走前景
    assert w._hint.testAttribute(Qt.WA_TransparentForMouseEvents)
    assert w._hint.testAttribute(Qt.WA_ShowWithoutActivating)
    assert w._hint.windowFlags() & Qt.WindowDoesNotAcceptFocus
    assert not w._hint.isModal()

    wait_for(qapp, lambda: not w._hint.isVisible(), timeout=2)
    assert not w._hint.isVisible()
    w.hide()


# ---- 點圓點或清單列直接跳轉（05 卡） ----

def mouse(w, kind: str, local, buttons=None):
    """對桌寵送一個左鍵滑鼠事件；local 是桌寵內的座標，全域座標用桌寵目前位置換算。"""
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication
    types = {"press": QEvent.MouseButtonPress, "move": QEvent.MouseMove,
             "release": QEvent.MouseButtonRelease}
    button = Qt.NoButton if kind == "move" else Qt.LeftButton
    if buttons is None:
        buttons = Qt.NoButton if kind == "release" else Qt.LeftButton
    global_pos = w.frameGeometry().topLeft() + local
    event = QMouseEvent(types[kind], QPointF(local), QPointF(global_pos), button, buttons,
                        Qt.NoModifier)
    QApplication.sendEvent(w, event)


def press_move_release(w, start, offsets=()):
    """左鍵按在 start，依序移動 offsets（相對按下點的位移），再放開；回傳放開前最後的位移。"""
    from PySide6.QtCore import QPoint
    mouse(w, "press", start)
    origin = w.frameGeometry().topLeft()  # 拖曳中桌寵會移動，滑鼠的全域位置以按下時為準
    last = QPoint(0, 0)
    for dx, dy in offsets:
        last = QPoint(dx, dy)
        local = start + last - (w.frameGeometry().topLeft() - origin)
        mouse(w, "move", local)
    local = start + last - (w.frameGeometry().topLeft() - origin)
    mouse(w, "release", local)


@pytest.fixture
def light_pet(pet_window, monkeypatch):
    """紅綠燈版桌寵（Windows），記下觸發的跳轉與存設定的次數。"""
    from PySide6.QtCore import QPoint

    def make(*sessions, labels=False):
        monkeypatch.setattr(pet.wt_jump, "supported", lambda: True)
        w = pet_window(*sessions)
        w.config["theme"] = "light"
        w.config["show_labels"] = labels
        w.refresh()
        w.move(QPoint(400, 300))
        w.started, w.saves = [], []
        monkeypatch.setattr(w._jumper, "start", w.started.append)
        monkeypatch.setattr(pet, "save_config", lambda c: w.saves.append(dict(c)))
        return w

    return make


def hit_of(w, sid):
    return next(rect for rect, s in w._hits if s and s.sid == sid)


def test_AC_JUMP_01_click_dot_jumps_to_that_session(light_pet):
    w = light_pet(("s1", "", "C:/t/s1.jsonl"), ("abc123", "", "C:/t/abc123.jsonl"))
    before = w.pos()

    press_move_release(w, hit_of(w, "abc123").center())

    assert w.started == ["C:/t/abc123.jsonl"]
    assert w.pos() == before  # 桌寵位置不變
    assert w.saves == []  # 不記位置
    assert not w._hint.isVisible()  # 點下去的當下不出提示


def test_AC_JUMP_02_click_row_text_jumps_when_labels_shown(light_pet):
    from PySide6.QtCore import QPoint
    w = light_pet(("s1", "", "C:/t/s1.jsonl"), ("abc123", "", "C:/t/abc123.jsonl"), labels=True)
    row = hit_of(w, "abc123")

    press_move_release(w, QPoint(row.right() - 3, row.center().y()))  # 點文字那一側
    press_move_release(w, QPoint(row.x() + pet.ROW_PAD + pet.ROW_DIAMETER // 2, row.center().y()))  # 點圓點

    assert w.started == ["C:/t/abc123.jsonl", "C:/t/abc123.jsonl"]


def test_AC_JUMP_07_drag_30px_from_dot_moves_and_saves_without_jump(light_pet):
    w = light_pet(("abc123", "", "C:/t/abc123.jsonl"))
    before = w.pos()

    press_move_release(w, hit_of(w, "abc123").center(), [(10, 0), (20, 0), (30, 0)])

    assert w.pos() == before + pet.QPoint(30, 0)  # 桌寵跟著滑鼠移到新位置
    assert w.saves and w.saves[-1]["pos"] == [w.x(), w.y()]  # 記住位置
    assert w.started == []  # 不切換分頁


def test_AC_OPS_04_move_within_drag_threshold_is_a_click(light_pet):
    from PySide6.QtWidgets import QApplication
    w = light_pet(("abc123", "", "C:/t/abc123.jsonl"))
    before = w.pos()
    threshold = QApplication.startDragDistance()

    press_move_release(w, hit_of(w, "abc123").center(), [(threshold, 0)])  # 剛好等於門檻：未超過

    assert w.pos() == before  # 桌寵不移動
    assert w.saves == []  # 不更新記住的位置
    assert w.started == ["C:/t/abc123.jsonl"]  # 視為點一下


def test_AC_OPS_04_move_just_over_threshold_is_a_drag(light_pet):
    from PySide6.QtWidgets import QApplication
    w = light_pet(("abc123", "", "C:/t/abc123.jsonl"))
    threshold = QApplication.startDragDistance()

    press_move_release(w, hit_of(w, "abc123").center(), [(threshold + 1, 0)])

    assert w.saves  # 超過門檻：算拖曳，記位置
    assert w.started == []


def test_AC_OPS_04_click_outside_dots_does_nothing(light_pet):
    from PySide6.QtCore import QPoint
    w = light_pet(("s1", "", "C:/t/s1.jsonl"), ("abc123", "", "C:/t/abc123.jsonl"))
    before = w.pos()
    gap = QPoint(hit_of(w, "s1").right() + pet.DOT_GAP // 2 + 1, hit_of(w, "s1").center().y())
    assert not any(rect.contains(gap) for rect, _s in w._hits)

    press_move_release(w, gap)  # 兩顆圓點之間的空隙
    press_move_release(w, QPoint(0, 0))  # 左上角邊緣

    assert w.started == []
    assert w.pos() == before
    assert w.saves == []


def test_AC_JUMP_12_grey_dot_without_session_does_nothing(light_pet):
    w = light_pet()
    assert len(w._hits) == 1 and w._hits[0][1] is None  # 只有 1 顆灰點

    press_move_release(w, w._hits[0][0].center())

    assert w.started == []
    assert w.saves == []


def test_AC_JUMP_08_click_on_non_windows_does_nothing(light_pet, monkeypatch, qapp):
    w = light_pet(("abc123", "", "C:/t/abc123.jsonl"))
    monkeypatch.setattr(pet.wt_jump, "supported", lambda: False)

    press_move_release(w, hit_of(w, "abc123").center())
    wait_for(qapp, lambda: False, timeout=0.1)

    assert w.started == []
    assert not w._hint.isVisible()


def test_animal_theme_click_does_not_move_or_save(light_pet):
    # 動物版的點擊（點小狼跳轉）屬於 06 卡；這裡只守「點一下不移動、不記位置」
    w = light_pet(("s1", "", "C:/t/s1.jsonl"))
    w.config["theme"] = "animal"
    w.refresh()
    before = w.pos()

    press_move_release(w, w._wolf_rect.center())

    assert w.pos() == before
    assert w.saves == []


# ---- 點小狼跳到最需要注意的 session（06 卡） ----

def fake(sid: str, state: str, start: float) -> Session:
    return Session(sid=sid, state=state, project=sid, cwd="", since=start, ts=start, start=start,
                   transcript=f"C:/t/{sid}.jsonl")


def test_AC_JUMP_09_wolf_target_is_earliest_of_most_urgent_state():
    sessions = [fake("A", "working", 100), fake("C", "waiting", 300), fake("B", "waiting", 200)]
    assert pet.wolf_jump_target(sessions).sid == "B"


def test_AC_JUMP_10_wolf_target_follows_waiting_done_working_thinking_order():
    assert pet.wolf_jump_target([fake("A", "thinking", 100), fake("B", "done", 200)]).sid == "B"
    assert pet.wolf_jump_target([fake("A", "thinking", 100), fake("B", "working", 200)]).sid == "B"
    assert pet.wolf_jump_target([fake("A", "idle", 100), fake("B", "thinking", 200)]).sid == "B"
    assert pet.wolf_jump_target([fake("A", "done", 300), fake("B", "waiting", 400)]).sid == "B"


def test_AC_JUMP_09_wolf_target_matches_wolf_display_state():
    # 跳去的 session 一定是小狼正在顯示的那個狀態
    for states in (("working", "done"), ("thinking", "working", "waiting"), ("idle", "thinking")):
        sessions = [fake(f"s{i}", st, i) for i, st in enumerate(states)]
        assert pet.wolf_jump_target(sessions).state == aggregate_state(sessions)


def test_AC_JUMP_11_wolf_target_none_when_all_idle_or_empty():
    assert pet.wolf_jump_target([]) is None
    assert pet.wolf_jump_target([fake("A", "idle", 100), fake("B", "idle", 200)]) is None


def test_AC_JUMP_11_wolf_target_none_when_busy_sessions_timed_out(sessions_dir):
    write_session(sessions_dir, "A", "working", age=601, start=100)
    write_session(sessions_dir, "B", "thinking", age=601, start=200)
    write_session(sessions_dir, "C", "done", age=1801, start=300)

    sessions = load_sessions(NOW)

    assert [s.state for s in sessions] == ["idle", "idle", "idle"]
    assert pet.wolf_jump_target(sessions) is None


@pytest.fixture
def animal_pet(qapp, sessions_dir, monkeypatch):
    """動物版桌寵（Windows）；sessions 為 (sid, 狀態, 首次出現, 距今秒數)，記下觸發的跳轉。"""
    from PySide6.QtCore import QPoint
    monkeypatch.setattr(pet, "CONFIG_FILE", sessions_dir / "config.json")  # 不碰真正的設定檔
    windows = []

    def make(*sessions, labels=False):
        monkeypatch.setattr(pet.wt_jump, "supported", lambda: True)
        now = time.time()
        for sid, state, start, age in sessions:
            data = {"state": state, "ts": now - age, "since": now - age, "start": start,
                    "sid": sid, "project": sid, "cwd": "", "transcript": f"C:/t/{sid}.jsonl"}
            (sessions_dir / f"{sid}.json").write_text(json.dumps(data), encoding="utf-8")
        config = dict(pet.DEFAULT_CONFIG, theme="animal", show_labels=labels)
        w = pet.PetWindow(config)
        windows.append(w)
        w.move(QPoint(400, 300))
        w.started, w.saves = [], []
        monkeypatch.setattr(w._jumper, "start", w.started.append)
        monkeypatch.setattr(pet, "save_config", lambda c: w.saves.append(dict(c)))
        return w

    yield make
    for w in windows:
        w.timer.stop()
        w.deleteLater()


def test_AC_JUMP_09_click_wolf_jumps_to_earliest_waiting(animal_pet):
    w = animal_pet(("A", "working", 100, 0), ("B", "waiting", 200, 0), ("C", "waiting", 300, 0))
    before = w.pos()

    press_move_release(w, w._wolf_rect.center())

    assert w.started == ["C:/t/B.jsonl"]
    assert w.pos() == before
    assert w.saves == []


def test_AC_JUMP_10_click_wolf_jumps_to_done_over_thinking(animal_pet):
    w = animal_pet(("A", "thinking", 100, 0), ("B", "done", 200, 0))

    press_move_release(w, w._wolf_rect.center())

    assert w.started == ["C:/t/B.jsonl"]


def test_AC_JUMP_11_click_wolf_all_idle_or_timed_out_does_nothing(animal_pet, qapp):
    w = animal_pet(("A", "idle", 100, 0), ("B", "working", 200, 601), ("C", "done", 300, 1801))
    assert {s.state for s in w.sessions} == {"idle"}

    press_move_release(w, w._wolf_rect.center())
    wait_for(qapp, lambda: False, timeout=0.1)

    assert w.started == []
    assert not w._hint.isVisible()


def test_AC_JUMP_11_click_wolf_without_sessions_does_nothing(animal_pet, qapp):
    w = animal_pet()

    press_move_release(w, w._wolf_rect.center())
    wait_for(qapp, lambda: False, timeout=0.1)

    assert w.started == []
    assert not w._hint.isVisible()


def test_AC_OPS_04_animal_click_dot_jumps_to_that_session(animal_pet):
    # 動物版小狼下方的小圓點：切到被點的那個 session，不是小狼挑的目標（07 卡）
    w = animal_pet(("A", "waiting", 100, 0), ("B", "done", 200, 0))
    assert w._hits and not any(w._wolf_rect.intersects(rect) for rect, _s in w._hits)
    before = w.pos()

    press_move_release(w, hit_of(w, "B").center())

    assert w.started == ["C:/t/B.jsonl"]
    assert w.pos() == before
    assert w.saves == []


def test_AC_JUMP_02_animal_click_row_text_jumps_when_labels_shown(animal_pet):
    from PySide6.QtCore import QPoint
    w = animal_pet(("A", "waiting", 100, 0), ("B", "done", 200, 0), labels=True)
    row = hit_of(w, "B")

    press_move_release(w, QPoint(row.right() - 2, row.center().y()))  # 文字端

    assert w.started == ["C:/t/B.jsonl"]


def test_AC_JUMP_07_animal_drag_from_dot_moves_without_jump(animal_pet):
    w = animal_pet(("A", "waiting", 100, 0), ("B", "done", 200, 0))
    before = w.pos()

    press_move_release(w, hit_of(w, "B").center(), [(10, 0), (20, 0), (30, 0)])

    assert w.pos() == before + pet.QPoint(30, 0)
    assert w.saves and w.saves[-1]["pos"] == [w.x(), w.y()]
    assert w.started == []


def test_AC_JUMP_08_animal_click_dot_on_non_windows_does_nothing(animal_pet, monkeypatch):
    w = animal_pet(("A", "waiting", 100, 0), ("B", "done", 200, 0))  # 只有 1 個 session 時不畫小圓點
    monkeypatch.setattr(pet.wt_jump, "supported", lambda: False)

    press_move_release(w, hit_of(w, "A").center())

    assert w.started == []


def test_animal_click_outside_wolf_and_dots_does_nothing(animal_pet):
    from PySide6.QtCore import QPoint
    w = animal_pet(("A", "waiting", 100, 0), ("B", "done", 200, 0))
    corner = QPoint(w.width() - 1, w.height() - 1)
    assert not w._wolf_rect.contains(corner)
    assert not any(rect.contains(corner) for rect, _s in w._hits)

    press_move_release(w, corner)

    assert w.started == []


def test_AC_JUMP_08_click_wolf_on_non_windows_does_nothing(animal_pet, monkeypatch):
    w = animal_pet(("A", "waiting", 100, 0))
    monkeypatch.setattr(pet.wt_jump, "supported", lambda: False)

    press_move_release(w, w._wolf_rect.center())

    assert w.started == []
