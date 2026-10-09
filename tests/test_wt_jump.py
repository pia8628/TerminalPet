"""wt_jump.py 標題擷取與分頁比對的測試（條文見 docs/specs/changes/click-to-terminal/delta.md JUMP 模組）。

標題擷取與分頁比對是純函式；叫出 WT／切換動作的順序與取消檢查用假的 Windows API 測。
紀錄檔一律是暫存資料夾裡的假資料，不讀真正的 ~/.claude/。
實際切換 WT 分頁（UI Automation）無法在 CI 自動測，列入人工驗收。
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import wt_jump  # noqa: E402
from wt_jump import find_matches, is_same_tab, parse_title, read_session_title, read_tail  # noqa: E402


def jsonl(*records) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records).encode("utf-8")


def ai(title):
    return {"type": "ai-title", "aiTitle": title, "sessionId": "abc123"}


def custom(title):
    return {"type": "custom-title", "customTitle": title, "sessionId": "abc123"}


def chat(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


# ---- 標題擷取 ----

def test_last_ai_title_wins():
    data = jsonl(ai("第一版標題"), chat("hi"), ai("任務進度條 Phase 4"), chat("ok"))
    assert parse_title(data) == "任務進度條 Phase 4"


def test_AC_JUMP_06_custom_title_overrides_later_ai_title():
    # /rename 之後 Claude Code 仍會反覆追加 ai-title，改名紀錄要優先
    data = jsonl(ai("任務進度條 Phase 4"), custom("跳轉功能"), ai("任務進度條 Phase 4"))
    assert parse_title(data) == "跳轉功能"


def test_AC_JUMP_06_last_custom_title_wins():
    data = jsonl(custom("第一次改名"), ai("自動"), custom("跳轉功能"))
    assert parse_title(data) == "跳轉功能"


def test_empty_custom_title_falls_back_to_ai_title():
    # 改名成空字串＝清除改名，回到自動標題
    data = jsonl(custom("跳轉功能"), ai("任務進度條 Phase 4"), custom(""))
    assert parse_title(data) == "任務進度條 Phase 4"


def test_title_is_only_stripped_not_rewritten():
    data = jsonl(ai("  ✳ .env 設定  "))
    assert parse_title(data) == "✳ .env 設定"


def test_AC_JUMP_14_no_title_lines_means_no_title():
    data = jsonl(chat("隨便聊"), chat('提到 "ai-title" 字樣的對話內容'), {"type": "summary"})
    assert parse_title(data) == ""


def test_title_mentioned_in_chat_content_is_ignored():
    # 對話內容裡出現像標題的文字（JSON 跳脫後）不能被當成標題
    data = jsonl(ai("真正的標題"), chat('{"type":"ai-title","aiTitle":"假的標題"}'))
    assert parse_title(data) == "真正的標題"


def test_broken_lines_are_skipped():
    half_written = '{"type":"ai-title","aiTitle":"寫到一半\n'.encode()
    data = jsonl(ai("真正的標題")) + half_written + b"\xff\xfe\"ai-title\"\n"
    assert parse_title(data) == "真正的標題"


@pytest.mark.parametrize("transcript", ["", "does/not/exist.jsonl"])
def test_AC_JUMP_17_missing_transcript_means_no_title(tmp_path, transcript):
    path = str(tmp_path / transcript) if transcript else ""
    assert read_session_title(path) == ""


def test_AC_JUMP_17_unreadable_transcript_means_no_title(tmp_path):
    # 路徑是資料夾 → 開檔失敗，比照沒有標題，不丟例外
    assert read_session_title(str(tmp_path)) == ""


def test_read_session_title_from_file(tmp_path):
    path = tmp_path / "abc123.jsonl"
    path.write_bytes(jsonl(ai("任務進度條 Phase 4"), custom("跳轉功能")))
    assert read_session_title(str(path).replace("\\", "/")) == "跳轉功能"


# ---- 只讀最後 1 MB ----

def test_title_before_last_1mb_is_ignored(tmp_path):
    path = tmp_path / "big.jsonl"
    filler = jsonl(chat("x" * 1000)) * 1100  # 約 1.1 MB 的對話內容
    path.write_bytes(jsonl(ai("太早的標題")) + filler)
    assert path.stat().st_size > wt_jump.TAIL_BYTES
    assert read_session_title(str(path)) == ""


def test_title_inside_last_1mb_is_found(tmp_path):
    path = tmp_path / "big.jsonl"
    filler = jsonl(chat("x" * 1000)) * 1100
    path.write_bytes(jsonl(ai("太早的標題")) + filler + jsonl(ai("最新標題")) + jsonl(chat("y")) * 20)
    assert read_session_title(str(path)) == "最新標題"


def test_partial_first_line_of_tail_is_dropped(tmp_path):
    # 截斷點剛好落在一行中間，殘段本身看起來像一筆完整的標題紀錄 → 必須丟掉，不能當成標題
    fake = json.dumps(ai("殘段標題"), ensure_ascii=False).encode("utf-8")
    tail_rest = b"\n" + jsonl(chat("z" * 40)) * 2
    padding = b"P" * 300  # 同一行前面的部分，落在截斷點之外
    content = padding + fake + tail_rest
    path = tmp_path / "cut.jsonl"
    path.write_bytes(content)
    limit = len(fake) + len(tail_rest)  # 截斷點剛好落在假標題的 { 前面
    data = read_tail(path, limit)
    assert b"aiTitle" not in data
    assert parse_title(data) == ""


def test_small_file_is_read_whole(tmp_path):
    path = tmp_path / "small.jsonl"
    content = jsonl(ai("第一行就是標題"))
    path.write_bytes(content)
    assert read_tail(path) == content


# ---- 分頁比對 ----

@pytest.mark.parametrize("tab", [
    "任務進度條 Phase 4",
    "✳ 任務進度條 Phase 4",
    "◐ 任務進度條 Phase 4",
    "◑ 任務進度條 Phase 4",
])
def test_AC_JUMP_05_status_prefixes_match(tab):
    assert is_same_tab(tab, "任務進度條 Phase 4")


@pytest.mark.parametrize("tab, title", [
    ("env", ".env"),             # AC-JUMP-21：session 標題本身不做任何改寫
    ("✳ env", ".env"),
    ("# env", "env"),            # 清單外的符號不算狀態前綴
    ("$ env", "env"),
    ("✳env", "env"),             # 前綴一定是「符號＋一個空白」
    ("✳ ✳ env", "env"),          # 只去一個前綴
    ("✳ 任務進度條 phase 4", "任務進度條 Phase 4"),  # 區分大小寫
    ("✳ 任務進度條 Phase 4 ", "任務進度條 Phase 4"),
    ("PowerShell", "任務進度條 Phase 4"),
    ("Claude Code", ""),         # 沒有標題不算同名
    ("", ""),
])
def test_AC_JUMP_21_not_same_tab(tab, title):
    assert not is_same_tab(tab, title)


def test_AC_JUMP_03_finds_the_second_tab():
    tabs = ["✳ 寫週報", "✳ 任務進度條 Phase 4", "PowerShell"]
    assert find_matches(tabs, "任務進度條 Phase 4") == [1]


def test_AC_JUMP_06_renamed_title_finds_renamed_tab():
    tabs = ["✳ 寫週報", "✳ 跳轉功能", "PowerShell"]
    assert find_matches(tabs, "跳轉功能") == [1]
    assert find_matches(tabs, "任務進度條 Phase 4") == []


def test_AC_JUMP_13_duplicate_tabs_are_counted():
    tabs = ["✳ 寫週報", "◐ 寫週報", "PowerShell"]
    assert find_matches(tabs, "寫週報") == [0, 1]


# ---- 主流程的分流（不碰 UI Automation） ----

def test_AC_JUMP_08_non_windows_is_unsupported(monkeypatch):
    monkeypatch.setattr(wt_jump.sys, "platform", "linux")
    assert not wt_jump.supported()
    assert wt_jump.jump_to_session("whatever.jsonl").code == wt_jump.UNSUPPORTED


def test_title_is_passed_to_window_search(monkeypatch, tmp_path):
    monkeypatch.setattr(wt_jump.sys, "platform", "win32")
    path = tmp_path / "abc123.jsonl"
    path.write_bytes(jsonl(ai("任務進度條 Phase 4")))
    calls = []
    monkeypatch.setattr(wt_jump, "_jump_windows",
                        lambda title, cancelled: calls.append(title) or wt_jump.JumpResult(wt_jump.OK, 1))
    assert wt_jump.jump_to_session(str(path)) == wt_jump.JumpResult(wt_jump.OK, 1)
    assert calls == ["任務進度條 Phase 4"]


def test_system_errors_become_failed_result(monkeypatch, tmp_path):
    monkeypatch.setattr(wt_jump.sys, "platform", "win32")
    path = tmp_path / "abc123.jsonl"
    path.write_bytes(jsonl(ai("任務進度條 Phase 4")))

    def boom(_title, _cancelled):
        raise OSError("UI Automation 失敗")

    monkeypatch.setattr(wt_jump, "_jump_windows", boom)
    assert wt_jump.jump_to_session(str(path)).code == wt_jump.FAILED


def test_AC_JUMP_17_system_errors_without_title_stay_not_found(monkeypatch):
    monkeypatch.setattr(wt_jump.sys, "platform", "win32")

    def boom(_title, _cancelled):
        raise OSError("列視窗失敗")

    monkeypatch.setattr(wt_jump, "_jump_windows", boom)
    assert wt_jump.jump_to_session("").code == wt_jump.NO_TITLE


# ======================================================================
# 叫出 WT／切換動作（假的 Windows API，記錄每個動作的順序，不碰真的視窗）
# ======================================================================

class FakeUser32:
    def __init__(self, log, iconic=(), refuse_foreground=False):
        self.log = log
        self.iconic = set(iconic)
        self.refuse = refuse_foreground
        self.foreground = 999  # 原本的前景視窗（不是 WT）

    def IsIconic(self, hwnd):
        return hwnd in self.iconic

    def ShowWindow(self, hwnd, _cmd):
        self.log.append(("restore", hwnd))
        self.iconic.discard(hwnd)
        return True

    def SetForegroundWindow(self, hwnd):
        self.log.append(("foreground", hwnd))
        if not self.refuse:
            self.foreground = hwnd
        return not self.refuse

    def GetForegroundWindow(self):
        return self.foreground


class FakeOle32:
    def CoInitializeEx(self, _reserved, _flags):
        return 0

    def CoUninitialize(self):
        pass


class FakeApi:
    def __init__(self, windows, **user32_options):
        """windows：{hwnd: [分頁標題, ...]}，依 Z-order（最上層在前）排列。"""
        self.windows = windows
        self.log = []
        self.user32 = FakeUser32(self.log, **user32_options)
        self.ole32 = FakeOle32()

    def wt_windows(self):
        return list(self.windows)


def install_fake(monkeypatch, api, select_error=False, on_select=None):
    class FakeUia:
        def __init__(self, _api):
            pass

        def tabs_of(self, hwnd):
            return [(name, (hwnd, i)) for i, name in enumerate(api.windows[hwnd])]

        def select(self, element):
            if on_select:
                on_select()
            if select_error:
                raise OSError("分頁已被關閉")
            api.log.append(("select", element))

        def close(self):
            pass

    monkeypatch.setattr(wt_jump.sys, "platform", "win32")
    monkeypatch.setattr(wt_jump, "_win", lambda: api)
    monkeypatch.setattr(wt_jump, "_Uia", FakeUia)
    monkeypatch.setattr(wt_jump, "_release", lambda _ptr: None)
    monkeypatch.setattr(wt_jump, "FOREGROUND_WAIT_SEC", 0.05)


def transcript_with(tmp_path, title) -> str:
    path = tmp_path / "abc123.jsonl"
    path.write_bytes(jsonl(ai(title)) if title else jsonl(chat("hi")))
    return str(path)


def selections(api):
    return [entry for entry in api.log if entry[0] == "select"]


def test_AC_JUMP_03_unique_tab_is_selected_and_brought_front(monkeypatch, tmp_path):
    api = FakeApi({10: ["✳ 寫週報", "✳ 任務進度條 Phase 4", "PowerShell"]})
    install_fake(monkeypatch, api)

    result = wt_jump.jump_to_session(transcript_with(tmp_path, "任務進度條 Phase 4"))

    assert result == wt_jump.JumpResult(wt_jump.OK, 1)
    assert api.log == [("select", (10, 1)), ("foreground", 10)]


def test_AC_JUMP_13_duplicate_tabs_bring_window_front_without_selecting(monkeypatch, tmp_path):
    api = FakeApi({10: ["✳ 寫週報", "✳ 寫週報", "PowerShell"]})
    install_fake(monkeypatch, api)

    result = wt_jump.jump_to_session(transcript_with(tmp_path, "寫週報"))

    assert result == wt_jump.JumpResult(wt_jump.AMBIGUOUS, 2)
    assert api.log == [("foreground", 10)]  # 視窗叫到前面，分頁選取不動


def test_AC_JUMP_14_no_title_brings_wt_front_without_selecting(monkeypatch, tmp_path):
    api = FakeApi({10: ["✳ 寫週報", "Claude Code"]})
    install_fake(monkeypatch, api)

    result = wt_jump.jump_to_session(transcript_with(tmp_path, ""))

    assert result.code == wt_jump.NO_TITLE
    assert api.log == [("foreground", 10)]


def test_AC_JUMP_15_no_match_brings_most_recent_wt_front(monkeypatch, tmp_path):
    api = FakeApi({20: ["✳ 寫週報"], 10: ["PowerShell"]}, iconic={20})  # 20 在 Z-order 最上層、已最小化
    install_fake(monkeypatch, api)

    result = wt_jump.jump_to_session(transcript_with(tmp_path, "不存在的標題"))

    assert result.code == wt_jump.NO_MATCH
    assert api.log == [("restore", 20), ("foreground", 20)]


def test_AC_JUMP_16_no_wt_window_switches_nothing(monkeypatch, tmp_path):
    api = FakeApi({})
    install_fake(monkeypatch, api)

    assert wt_jump.jump_to_session(transcript_with(tmp_path, "寫週報")).code == wt_jump.NO_WINDOW
    assert wt_jump.jump_to_session("").code == wt_jump.NO_TITLE
    assert api.log == []


def test_AC_JUMP_17_fake_or_missing_transcript_is_treated_as_no_title(monkeypatch, tmp_path):
    api = FakeApi({10: ["✳ 寫週報"]})
    install_fake(monkeypatch, api)

    for transcript in ("", str(tmp_path / "gone.jsonl")):  # set_state.py 的假 session／紀錄檔已刪除
        api.log.clear()
        assert wt_jump.jump_to_session(transcript).code == wt_jump.NO_TITLE
        assert api.log == [("foreground", 10)]


def test_AC_JUMP_21_dot_env_does_not_switch_to_env_tab(monkeypatch, tmp_path):
    api = FakeApi({10: ["✳ env", "PowerShell"]})
    install_fake(monkeypatch, api)

    result = wt_jump.jump_to_session(transcript_with(tmp_path, ".env"))

    assert result.code == wt_jump.NO_MATCH
    assert selections(api) == []


def test_AC_JUMP_19_tab_closed_before_select_fails_without_other_tab(monkeypatch, tmp_path):
    api = FakeApi({10: ["✳ 寫週報", "PowerShell"]})
    install_fake(monkeypatch, api, select_error=True)

    result = wt_jump.jump_to_session(transcript_with(tmp_path, "寫週報"))

    assert result.code == wt_jump.FAILED
    assert api.log == []  # 不會改去切其他分頁，也不會再帶視窗到前面


def test_AC_JUMP_19_foreground_refused_is_failed(monkeypatch, tmp_path):
    api = FakeApi({10: ["✳ 寫週報"]}, refuse_foreground=True)
    install_fake(monkeypatch, api)

    result = wt_jump.jump_to_session(transcript_with(tmp_path, "寫週報"))

    assert result.code == wt_jump.FAILED


@pytest.mark.parametrize("cancel_after, expected_log", [
    (0, []),                                     # 查找完就取消：不還原、不選分頁、不帶前景
    (1, [("restore", 10)]),                      # 還原後取消：不再選分頁
    (2, [("restore", 10), ("select", (10, 0))]),  # 選分頁後取消：不再帶前景
])
def test_AC_JUMP_19_cancel_is_checked_before_every_switch_action(monkeypatch, tmp_path, cancel_after, expected_log):
    api = FakeApi({10: ["✳ 寫週報"]}, iconic={10})
    install_fake(monkeypatch, api)

    def cancelled():
        return len(api.log) >= cancel_after

    result = wt_jump.jump_to_session(transcript_with(tmp_path, "寫週報"), cancelled)

    assert result.code == wt_jump.FAILED
    assert api.log == expected_log


def test_cancel_also_stops_bringing_wt_front(monkeypatch, tmp_path):
    api = FakeApi({10: ["PowerShell"]}, iconic={10})
    install_fake(monkeypatch, api)

    result = wt_jump.jump_to_session(transcript_with(tmp_path, "寫週報"), lambda: True)

    assert result.code == wt_jump.NO_MATCH
    assert api.log == []
