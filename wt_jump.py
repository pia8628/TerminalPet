"""切換到 session 所在的 Windows Terminal 分頁（顯示端，只讀不寫）。

在背景執行緒中呼叫 jump_to_session()：
1. 從 session 的對話紀錄檔（JSONL）最後 1 MB 取出 session 標題
   ——只解析標題那幾行，不讀對話內容，也不寫入紀錄檔
2. 用 Windows UI Automation 列出所有 Windows Terminal 視窗的分頁，找出同名分頁
3. 只有一個同名分頁時：視窗最小化就先還原 → 選中分頁 → 把視窗帶到最前面；
   沒有標題／沒有同名分頁／撞名時，只把（最近使用的）WT 視窗帶到最前面，不改分頁選取

呼叫端可傳入 cancelled()（逾時或桌寵關閉時回傳 True）：每一個切換動作
（還原、選分頁、帶到最前面）開始前都會檢查，取消後不再開始新的動作。

標題擷取與分頁比對是不依賴 Windows 的純函式（方便測試）。
UI Automation 只用 ctypes 直接呼叫系統內建的 COM 元件，不需要額外套件；
非 Windows 系統 import 本模組不會出錯，只是 supported() 為 False。
"""

import json
import sys
import time
import uuid
from dataclasses import dataclass
from functools import cache
from pathlib import Path

# 只看紀錄檔最後這麼多位元組（Claude Code 會在對話中反覆寫入標題，最後一筆通常距檔尾幾十 KB）
TAIL_BYTES = 1024 * 1024

# Claude Code 加在分頁標題最前面的「狀態符號＋空白」；清單以外的字元一律不算前綴
STATUS_PREFIXES = ("✳ ", "◐ ", "◑ ")  # U+2733 閒置、U+25D0／U+25D1 執行中（聚焦時交替）

# 跳轉結果代碼（顯示端依此決定要不要出提示）
OK = "ok"                    # 已選中唯一的同名分頁，WT 在最前面
NO_TITLE = "no_title"        # 沒有標題：沒有紀錄檔路徑、檔案不存在／讀不到、找不到標題行
NO_WINDOW = "no_window"      # 沒有任何 WT 視窗
NO_MATCH = "no_match"        # 有標題，但沒有同名分頁
AMBIGUOUS = "ambiguous"      # 同名分頁不只一個（matches 是數量）
FAILED = "failed"            # 有唯一同名分頁，但切換過程失敗（選取失敗、前景被拒、被取消等）
UNSUPPORTED = "unsupported"  # 非 Windows


@dataclass
class JumpResult:
    code: str
    matches: int = 0  # 找到的同名分頁數量


def supported() -> bool:
    return sys.platform == "win32"


# ======================================================================
# 標題擷取與分頁比對（純函式，不依賴 Windows）
# ======================================================================

def read_tail(path: Path, limit: int = TAIL_BYTES) -> bytes:
    """讀檔案最後 limit 個位元組；有截斷時切掉第一行殘段（只剩完整的行）。"""
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        if size <= limit:
            f.seek(0)
            return f.read()
        f.seek(size - limit)
        data = f.read(limit)
    newline = data.find(b"\n")
    return data[newline + 1:] if newline >= 0 else b""


def parse_title(data: bytes) -> str:
    """從 JSONL 內容取 session 標題；沒有標題回傳空字串。

    最後一筆改名（custom-title）優先；最後一筆改名是空字串（清除改名）時，
    退回最後一筆自動標題（ai-title）。標題只去頭尾空白，不做其他改寫。
    """
    custom = ai = None
    for line in data.split(b"\n"):
        # 先用位元組過濾，只有標題行才做 JSON 解析，不碰對話內容
        if b'"custom-title"' not in line and b'"ai-title"' not in line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:  # 含 UnicodeDecodeError
            continue
        if not isinstance(obj, dict):
            continue
        kind = obj.get("type")
        if kind == "custom-title" and isinstance(obj.get("customTitle"), str):
            custom = obj["customTitle"]
        elif kind == "ai-title" and isinstance(obj.get("aiTitle"), str):
            ai = obj["aiTitle"]
    for title in (custom, ai):
        if title and title.strip():
            return title.strip()
    return ""


def read_session_title(transcript: str) -> str:
    """讀 session 標題；沒有路徑、檔案不存在或讀不到時回傳空字串（＝沒有標題）。"""
    if not transcript:
        return ""
    try:
        return parse_title(read_tail(Path(transcript)))
    except OSError:
        return ""


def is_same_tab(tab: str, title: str) -> bool:
    """分頁標題與 session 標題完全相同，或恰好是「一個狀態前綴＋session 標題」才算同名。"""
    if not title:
        return False
    return tab == title or any(tab == prefix + title for prefix in STATUS_PREFIXES)


def find_matches(tabs: list[str], title: str) -> list[int]:
    """回傳同名分頁在 tabs 中的位置。"""
    return [i for i, tab in enumerate(tabs) if is_same_tab(tab, title)]


# ======================================================================
# 跳轉主流程（在背景執行緒呼叫）
# ======================================================================

def jump_to_session(transcript: str, cancelled=None) -> JumpResult:
    """切到 session 所在的 WT 分頁；任何錯誤都轉成結果代碼，不往外丟例外。

    cancelled：無參數函式，回傳 True 表示已逾時或桌寵關閉，不要再開始新的切換動作。
    """
    if not supported():
        return JumpResult(UNSUPPORTED)
    cancelled = cancelled or (lambda: False)
    title = read_session_title(transcript)
    try:
        return _jump_windows(title, cancelled)
    except Exception:  # 背景執行緒不能因為系統呼叫失敗而中止
        # 沒有標題時本來就跳不過去，提示維持「找不到」；有標題才算切換失敗
        return JumpResult(FAILED if title else NO_TITLE)


def _jump_windows(title: str, cancelled) -> JumpResult:
    api = _win()
    # 查找：列出所有 WT 視窗（依 Z-order，最上層在前＝最近使用過的）
    hwnds = api.wt_windows()
    if not title:
        # 沒有標題（含假 session、紀錄檔不見）：只把最近使用的 WT 叫到前面
        if hwnds:
            _bring_to_front(api, hwnds[0], cancelled)
        return JumpResult(NO_TITLE)
    if not hwnds:
        return JumpResult(NO_WINDOW)
    initialized = api.ole32.CoInitializeEx(None, COINIT_MULTITHREADED) in (0, 1)  # S_OK／S_FALSE
    try:
        uia = _Uia(api)
        elements = []
        try:
            # 查找：列出每個 WT 視窗的所有分頁
            names, owners = [], []
            for hwnd in hwnds:
                try:
                    tabs = uia.tabs_of(hwnd)
                except OSError:
                    continue  # 視窗剛好被關掉等情況，略過這個視窗
                for name, element in tabs:
                    elements.append(element)
                    names.append(name)
                    owners.append(hwnd)
            found = find_matches(names, title)
            if not found:
                _bring_to_front(api, hwnds[0], cancelled)
                return JumpResult(NO_MATCH)
            if len(found) > 1:
                # 撞名：把含同名分頁、最近使用的那個視窗叫到前面，分頁選取不動
                _bring_to_front(api, owners[found[0]], cancelled)
                return JumpResult(AMBIGUOUS, len(found))
            index = found[0]
            # 切換：還原 → 選分頁 → 帶到最前面
            return _switch(api, uia, owners[index], elements[index], cancelled)
        finally:
            for element in elements:
                _release(element)
            uia.close()
    finally:
        if initialized:
            api.ole32.CoUninitialize()


def _restore(api, hwnd: int) -> None:
    if api.user32.IsIconic(hwnd):
        # 只對最小化的視窗還原；對最大化的視窗呼叫會把它縮成一般大小
        api.user32.ShowWindow(hwnd, SW_RESTORE)


def _bring_to_front(api, hwnd: int, cancelled) -> None:
    """跳不過去時盡量把 WT 視窗叫到最前面；不選分頁、不判定成敗（提示照樣顯示）。"""
    if cancelled():
        return
    _restore(api, hwnd)
    if cancelled():
        return
    api.user32.SetForegroundWindow(hwnd)


def _switch(api, uia, hwnd: int, element, cancelled) -> JumpResult:
    # 每個動作開始前都檢查是否已取消（逾時或桌寵關閉）；已在執行中的動作無法中斷
    if cancelled():
        return JumpResult(FAILED, 1)
    _restore(api, hwnd)
    if cancelled():
        return JumpResult(FAILED, 1)
    try:
        uia.select(element)  # WT 選中分頁時通常會順帶把視窗帶到前景
    except OSError:
        return JumpResult(FAILED, 1)  # 例如分頁在切換前被關閉
    if cancelled():
        return JumpResult(FAILED, 1)
    api.user32.SetForegroundWindow(hwnd)
    deadline = time.monotonic() + FOREGROUND_WAIT_SEC
    while api.user32.GetForegroundWindow() != hwnd:
        if time.monotonic() > deadline:
            return JumpResult(FAILED, 1)  # 例如 Windows 拒絕切前景、只在工作列閃爍
        time.sleep(0.05)
    return JumpResult(OK, 1)


# ======================================================================
# Windows API（ctypes）
# ======================================================================

WT_CLASS = "CASCADIA_HOSTING_WINDOW_CLASS"
SW_RESTORE = 9
COINIT_MULTITHREADED = 0
CLSCTX_INPROC_SERVER = 1
FOREGROUND_WAIT_SEC = 0.5  # 選分頁後等 WT 成為前景的上限

UIA_SelectionItemPatternId = 10010
UIA_TabItemControlTypeId = 50019
TreeScope_Descendants = 4

# COM 介面方法在 vtable 中的位置（含 IUnknown 的 0～2）
IUIAutomation_ElementFromHandle = 6
IUIAutomation_CreateTrueCondition = 21
IUIAutomationElement_FindAll = 6
IUIAutomationElement_GetCurrentPattern = 16
IUIAutomationElement_get_CurrentControlType = 21
IUIAutomationElement_get_CurrentName = 23
IUIAutomationElementArray_get_Length = 3
IUIAutomationElementArray_GetElement = 4
IUIAutomationSelectionItemPattern_Select = 3


def _guid(text: str):
    import ctypes

    class GUID(ctypes.Structure):
        _fields_ = [("data", ctypes.c_ubyte * 16)]

    return GUID.from_buffer_copy(uuid.UUID(text).bytes_le)


@cache
def _win():
    """載入並設定用到的系統 DLL 函式（只在 Windows、第一次跳轉時執行）。"""
    import ctypes
    from ctypes import wintypes

    class Api:
        pass

    api = Api()
    api.user32 = user32 = ctypes.WinDLL("user32", use_last_error=True)
    api.ole32 = ole32 = ctypes.WinDLL("ole32")
    api.oleaut32 = oleaut32 = ctypes.WinDLL("oleaut32")

    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [enum_proc, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole32.CoInitializeEx.restype = ctypes.c_long
    ole32.CoUninitialize.argtypes = []
    ole32.CoUninitialize.restype = None
    ole32.CoCreateInstance.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                                       ctypes.c_void_p, ctypes.c_void_p]
    ole32.CoCreateInstance.restype = ctypes.c_long
    oleaut32.SysFreeString.argtypes = [ctypes.c_void_p]
    oleaut32.SysFreeString.restype = None

    def wt_windows() -> list[int]:
        """依 Z-order（最上層在前）列出 WT 頂層視窗。"""
        found = []
        buf = ctypes.create_unicode_buffer(256)

        def callback(hwnd, _lparam):
            user32.GetClassNameW(hwnd, buf, 256)
            if buf.value == WT_CLASS:
                found.append(hwnd)
            return True

        user32.EnumWindows(enum_proc(callback), 0)
        return found

    api.wt_windows = wt_windows
    api.CLSID_CUIAutomation = _guid("{FF48DBA4-60EF-4201-AA87-54103EEF594E}")
    api.IID_IUIAutomation = _guid("{30CBE57D-D9D0-452A-AB13-7AC5AC4825EE}")
    api.IID_SelectionItemPattern = _guid("{A8EFA66A-0FDA-421A-9194-38021F3578EA}")
    return api


def _vcall(ptr, index: int, *args) -> int:
    """以 vtable 位置呼叫 COM 方法，回傳 HRESULT；參數一律當指標大小傳遞。"""
    import ctypes
    vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    argtypes = [ctypes.c_int if isinstance(a, ctypes.c_int) else ctypes.c_void_p for a in args]
    method = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argtypes)(vtbl[index])
    return method(ptr, *args)


def _check(hr: int, what: str) -> None:
    if hr != 0:
        raise OSError(f"{what} 失敗 HRESULT=0x{hr & 0xFFFFFFFF:08X}")


def _release(ptr) -> None:
    import ctypes
    if ptr:
        vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])(ptr)


class _Uia:
    """IUIAutomation 的最小包裝：列出視窗底下的分頁、選中分頁。每個執行緒各建一個。"""

    def __init__(self, api):
        import ctypes
        self._ctypes = ctypes
        self._api = api
        self._ptr = ctypes.c_void_p()
        _check(api.ole32.CoCreateInstance(ctypes.byref(api.CLSID_CUIAutomation), None, CLSCTX_INPROC_SERVER,
                                          ctypes.byref(api.IID_IUIAutomation), ctypes.byref(self._ptr)),
               "CoCreateInstance(CUIAutomation)")

    def close(self) -> None:
        _release(self._ptr)
        self._ptr = self._ctypes.c_void_p()

    def tabs_of(self, hwnd: int) -> list:
        """回傳 [(分頁名稱, 元素指標)]；元素指標由呼叫端 _release。"""
        ctypes = self._ctypes
        root, cond, arr = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
        tabs = []
        try:
            _check(_vcall(self._ptr, IUIAutomation_ElementFromHandle, ctypes.c_void_p(hwnd), ctypes.byref(root)),
                   "ElementFromHandle")
            _check(_vcall(self._ptr, IUIAutomation_CreateTrueCondition, ctypes.byref(cond)), "CreateTrueCondition")
            _check(_vcall(root, IUIAutomationElement_FindAll, ctypes.c_int(TreeScope_Descendants), cond,
                          ctypes.byref(arr)), "FindAll")
            length = ctypes.c_int()
            _check(_vcall(arr, IUIAutomationElementArray_get_Length, ctypes.byref(length)), "get_Length")
            for i in range(length.value):
                item = ctypes.c_void_p()
                if _vcall(arr, IUIAutomationElementArray_GetElement, ctypes.c_int(i), ctypes.byref(item)) != 0:
                    continue
                control_type = ctypes.c_int()
                _vcall(item, IUIAutomationElement_get_CurrentControlType, ctypes.byref(control_type))
                if control_type.value != UIA_TabItemControlTypeId:
                    _release(item)
                    continue
                tabs.append((self._name_of(item), item))
        except OSError:
            for _name, item in tabs:
                _release(item)
            raise
        finally:
            _release(arr)
            _release(cond)
            _release(root)
        return tabs

    def _name_of(self, item) -> str:
        ctypes = self._ctypes
        bstr = ctypes.c_void_p()
        if _vcall(item, IUIAutomationElement_get_CurrentName, ctypes.byref(bstr)) != 0 or not bstr.value:
            return ""
        try:
            return ctypes.wstring_at(bstr.value)
        finally:
            self._api.oleaut32.SysFreeString(bstr)

    def select(self, item) -> None:
        ctypes = self._ctypes
        pattern, selection = ctypes.c_void_p(), ctypes.c_void_p()
        try:
            _check(_vcall(item, IUIAutomationElement_GetCurrentPattern, ctypes.c_int(UIA_SelectionItemPatternId),
                          ctypes.byref(pattern)), "GetCurrentPattern")
            if not pattern:
                raise OSError("分頁不支援 SelectionItem")
            # GetCurrentPattern 回傳 IUnknown，要 QueryInterface 成 IUIAutomationSelectionItemPattern
            _check(_vcall(pattern, 0, ctypes.byref(self._api.IID_SelectionItemPattern), ctypes.byref(selection)),
                   "QueryInterface(SelectionItem)")
            _check(_vcall(selection, IUIAutomationSelectionItemPattern_Select), "Select")
        finally:
            _release(selection)
            _release(pattern)
