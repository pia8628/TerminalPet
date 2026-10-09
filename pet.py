"""TerminalPet — 監看 Claude Code 狀態的桌面小工具。

一個透明、無邊框、永遠置頂的小視窗，讀取 ~/.terminalpet/sessions/ 底下
每個 Claude Code session 的狀態檔，每個 session 各顯示一個燈。
可用滑鼠拖曳；紅綠燈版左鍵點一下某個 session 的圓點（或清單列）可切到它的終端機分頁；
右鍵選單可切換外觀、顯示專案名稱、桌面通知等。

兩種外觀（啟動參數會記住，之後不帶參數就沿用上次的外觀）：
    python pet.py            動物版（小狼顯示最需要注意的狀態，下方是各 session 燈）
    python pet.py light      辦公室紅綠燈版（每個 session 一個小圓點）
"""

import json
import sys
import threading
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QLockFile, QObject, QPoint, QRect, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QBrush,
    QColor,
    QDesktopServices,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QMessageBox, QSystemTrayIcon, QToolTip, QWidget

import wt_jump

STATE_DIR = Path.home() / ".terminalpet"
# 每個 Claude Code session 各寫一個狀態檔到這個資料夾（由 pet-state.sh 寫入）。
SESSIONS_DIR = STATE_DIR / "sessions"
CONFIG_FILE = STATE_DIR / "config.json"
LOCK_FILE = STATE_DIR / "pet.lock"
if getattr(sys, "frozen", False):
    # PyInstaller 凍結後 __file__ 不指向真實安裝路徑，資源改從 _MEIPASS 讀取
    ASSETS_DIR = Path(sys._MEIPASS) / "assets"
else:
    ASSETS_DIR = Path(__file__).resolve().parent / "assets"

# 輪詢間隔（毫秒）。Windows 的 QFileSystemWatcher 對「檔案覆寫」偵測不可靠，
# 實務上是靠這個輪詢兜底，所以間隔就是使用者感受到的最壞延遲，設短一點。
POLL_MS = 250

# 切換到終端機：處理超過這個時間仍未完成就視為切換失敗；跳轉提示顯示這麼久後自動消失
JUMP_TIMEOUT_MS = 3000
HINT_MS = 3000

# 逾時規則依狀態而定：
# - waiting（等你批准／回答）不會自己消失，你沒處理就一直亮著
# - thinking/working 太久沒有任何 hook 更新，多半是被 Esc 中斷（中斷不會觸發 Stop）
# - done 是「換你了」的訊號，保留一段時間讓你回來看得到
BUSY_TIMEOUT_SEC = 10 * 60
DONE_TIMEOUT_SEC = 30 * 60
# 超過這麼久沒更新的 session 檔視為過期（終端機直接關掉時 SessionEnd 不會觸發），直接清掉
SESSION_STALE_SEC = 3 * 3600
WAITING_STALE_SEC = 12 * 3600

# 數字越大越需要你注意。小狼顯示、系統匣圖示都取最高者。
STATE_PRIORITY = {
    "waiting": 4,
    "done": 3,
    "working": 2,
    "thinking": 1,
    "idle": 0,
}
STATE_LABEL = {
    "waiting": "等你處理",
    "done": "完成",
    "working": "執行中",
    "thinking": "思考中",
    "idle": "閒置",
}
STATE_COLORS = {
    "thinking": "#f5c518",  # 黃：思考／處理中
    "working": "#2ecc71",   # 綠：自己在跑
    "waiting": "#e74c3c",   # 紅：需要你介入（會閃）
    "done": "#3498db",      # 藍：完成，換你了
    "idle": "#7f8c8d",      # 灰：閒置
}

# ---- 動物版：小狼圖檔（在 assets/），找不到檔案時退回 emoji 佔位 ----
WOLF_IMG = {s: ASSETS_DIR / f"wolf_{s}.png" for s in ("thinking", "working", "waiting", "done")}
WOLF_IMG["idle"] = ASSETS_DIR / "wolf_sleeping.png"
STATE_ART = {
    "thinking": "🐺💭",
    "working": "🐺⚙️",
    "waiting": "🐺❗",
    "done": "🐺✅",
    "idle": "🐺💤",
}
ANIMAL_SIZE = 120  # 小狼顯示邊長（px）

# ---- 燈號尺寸 ----
LIGHT_DIAMETER = 24  # 紅綠燈版圓點直徑（px）
STRIP_DIAMETER = 14  # 動物版小狼下方的 session 圓點
ROW_DIAMETER = 12    # 顯示專案名稱時，每列前面的圓點
DOT_GAP = 6
MARGIN = 3
ROW_HEIGHT = 22
ROW_PAD = 8

DEFAULT_CONFIG = {
    "theme": "animal",     # animal | light
    "show_labels": False,  # 顯示專案名稱
    "notify": False,       # session 需要你／完成時跳桌面通知
    "pos": None,           # 上次拖曳到的左上角座標
}


# ======================================================================
# 狀態讀取（不依賴 Qt，方便測試）
# ======================================================================

@dataclass
class Session:
    sid: str
    state: str      # 套用逾時規則後的有效狀態
    project: str
    cwd: str
    since: float    # 進入目前狀態的時間
    ts: float       # 最後一次 hook 更新
    start: float    # 第一次出現，用來固定排序
    label: str = ""
    transcript: str = ""  # 對話紀錄檔路徑（跳轉時讀 session 標題用；假 session 為空）


def effective_state(raw: str, age: float) -> str:
    if raw not in STATE_PRIORITY:
        return "idle"  # 含舊版的 sleeping
    if raw in ("thinking", "working") and age > BUSY_TIMEOUT_SEC:
        return "idle"
    if raw == "done" and age > DONE_TIMEOUT_SEC:
        return "idle"
    return raw


def load_sessions(now: float | None = None, cache: dict | None = None) -> list[Session]:
    """讀取所有 session 檔，套用逾時規則、清掉過期檔，依首次出現時間排序。

    cache：{檔名: 上次成功解析的內容}。檔案剛好在寫入中讀不到時沿用上次的，
    避免燈號在那一瞬間少一顆而閃動。
    """
    now = time.time() if now is None else now
    cache = {} if cache is None else cache
    sessions = []
    seen_names = set()
    for path in SESSIONS_DIR.glob("*.json"):
        seen_names.add(path.name)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cache[path.name] = data
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            data = cache.get(path.name)
            if data is None:
                continue
        try:
            ts = float(data.get("ts", 0))
            since = float(data.get("since", ts))
            start = float(data.get("start", ts))
        except (TypeError, ValueError):
            continue
        age = now - ts
        state = effective_state(data.get("state", "idle"), age)
        stale = WAITING_STALE_SEC if state == "waiting" else SESSION_STALE_SEC
        if age > stale:
            try:
                path.unlink()
            except OSError:
                pass
            continue
        sid = str(data.get("sid") or path.stem)
        sessions.append(Session(
            sid=sid,
            state=state,
            project=str(data.get("project") or sid[:8]),
            cwd=str(data.get("cwd") or ""),
            since=since,
            ts=ts,
            start=start,
            transcript=str(data.get("transcript") or ""),
        ))
    for name in list(cache):
        if name not in seen_names:
            del cache[name]

    sessions.sort(key=lambda s: (s.start, s.sid))
    # 同一個專案開了好幾個 session 時加編號區分
    totals = Counter(s.project for s in sessions)
    counter = Counter()
    for s in sessions:
        counter[s.project] += 1
        s.label = s.project if totals[s.project] == 1 else f"{s.project} #{counter[s.project]}"
    return sessions


def aggregate_state(sessions: list[Session]) -> str:
    if not sessions:
        return "idle"
    return max((s.state for s in sessions), key=STATE_PRIORITY.__getitem__)


def format_elapsed(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return "剛剛"  # 不顯示秒數，避免文字每秒變寬變窄
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} 分"
    return f"{minutes // 60} 小時 {minutes % 60} 分"


def session_text(s: Session, now: float) -> str:
    if s.state == "idle":
        return f"{s.label}  {STATE_LABEL[s.state]}"
    return f"{s.label}  {STATE_LABEL[s.state]} {format_elapsed(now - s.since)}"


# ======================================================================
# 設定與開機自動啟動
# ======================================================================

def load_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    try:
        config.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    if config["theme"] not in ("animal", "light"):
        config["theme"] = "animal"
    return config


def save_config(config: dict) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "TerminalPet"


def autostart_supported() -> bool:
    return sys.platform == "win32"


def autostart_enabled() -> bool:
    if not autostart_supported():
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY) as key:
            winreg.QueryValueEx(key, AUTOSTART_NAME)
            return True
    except OSError:
        return False


def set_autostart(enabled: bool) -> None:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            # 用 pythonw 啟動，開機時不會跳出終端機視窗；外觀沿用 config.json
            exe = Path(sys.executable)
            pythonw = exe.with_name("pythonw.exe")
            if pythonw.exists():
                exe = pythonw
            winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ,
                              f'"{exe}" "{Path(__file__).resolve()}"')
        else:
            try:
                winreg.DeleteValue(key, AUTOSTART_NAME)
            except FileNotFoundError:
                pass


# ======================================================================
# 視窗
# ======================================================================

def dot_pixmap(state: str, size: int = 32) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(0, 0, 0, 120), 2))
    p.setBrush(QColor(STATE_COLORS[state]))
    p.drawEllipse(2, 2, size - 4, size - 4)
    p.end()
    return pm


class JumpRunner(QObject):
    """在背景執行緒跑「切換到終端機」（讀標題＋UI Automation），結果用 Qt signal 送回主執行緒。

    背景處理期間主執行緒照常跑事件迴圈，桌寵的燈號、閃燈、拖曳、右鍵都不受影響。
    同一時間只處理一個跳轉；每次跳轉帶一個世代編號與取消旗標：
    - 主執行緒計時，超過 JUMP_TIMEOUT_MS 就設取消旗標並回報 failed
    - 背景執行緒在每個切換動作開始前檢查旗標與世代編號，不符就放棄
    - 背景結果晚到（世代編號已不是進行中的那個）就丟掉，不會再回報第二次
    """

    finished = Signal(object)  # wt_jump.JumpResult，在主執行緒收到；每次跳轉只回報一次
    _done = Signal(int, object)  # 背景執行緒 → 主執行緒：（世代編號, 結果）

    def __init__(self, parent=None, job=None, timeout_ms: int | None = None):
        super().__init__(parent)
        self._job = job  # 測試可換成假的跳轉函式；None 表示用 wt_jump.jump_to_session
        self._timeout_ms = JUMP_TIMEOUT_MS if timeout_ms is None else timeout_ms
        self._generation = 0
        self._active: int | None = None  # 進行中的世代編號；None 表示閒置
        self._cancel: threading.Event | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)
        self._done.connect(self._on_done)

    @property
    def busy(self) -> bool:
        return self._active is not None

    def start(self, transcript: str) -> bool:
        """開始跳轉；已有跳轉處理中時忽略並回傳 False。"""
        if self.busy:
            return False
        self._generation += 1
        generation = self._generation
        cancel = threading.Event()
        self._active, self._cancel = generation, cancel

        def cancelled() -> bool:
            return cancel.is_set() or self._active != generation

        self._timer.start(self._timeout_ms)
        threading.Thread(target=self._run, args=(generation, transcript, cancelled),
                         daemon=True, name="wt-jump").start()
        return True

    def cancel(self) -> None:
        """取消進行中的跳轉（桌寵關閉時呼叫）；不回報結果。"""
        self._timer.stop()
        if self._cancel:
            self._cancel.set()
        self._active, self._cancel = None, None

    def _run(self, generation: int, transcript: str, cancelled) -> None:
        job = self._job or wt_jump.jump_to_session
        try:
            result = job(transcript, cancelled)
        except Exception:  # 背景執行緒的錯誤不能讓桌寵中止
            result = wt_jump.JumpResult(wt_jump.FAILED)
        self._done.emit(generation, result)  # 跨執行緒發送，Qt 會排進主執行緒處理

    def _on_done(self, generation: int, result) -> None:
        if generation != self._active:
            return  # 已逾時或已取消：晚到的結果丟掉，不顯示第二個提示
        self._timer.stop()
        self._active, self._cancel = None, None
        self.finished.emit(result)

    def _on_timeout(self) -> None:
        if not self.busy:
            return
        self.cancel()  # 不再開始新的切換動作
        self.finished.emit(wt_jump.JumpResult(wt_jump.FAILED))


def jump_hint_text(result) -> str | None:
    """依跳轉結果決定跳轉提示的文字；成功或非 Windows 時不提示（回傳 None）。"""
    if result.code == wt_jump.AMBIGUOUS:
        return f"有 {result.matches} 個分頁同名，請手動切換"
    if result.code in (wt_jump.NO_TITLE, wt_jump.NO_WINDOW, wt_jump.NO_MATCH):
        return "找不到這個 session 的分頁"
    if result.code == wt_jump.FAILED:
        return "切換失敗，請手動切換"
    return None


class JumpHint(QLabel):
    """跳轉提示：桌寵旁邊的小提示框，HINT_MS 後自動消失，不需要按任何按鈕。

    不搶焦點（剛叫到前面的 WT 不會被搶走前景）、不接收滑鼠（不擋桌寵的拖曳、右鍵、點擊）。
    """

    GAP = 6  # 與桌寵的間距

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                            | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        font = QFont()
        font.setPointSize(9)
        self.setFont(font)
        self.setStyleSheet("QLabel { background: #2b2b2b; color: #f0f0f0;"
                           " border: 1px solid #5a5a5a; padding: 6px 10px; }")
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_near(self, text: str, anchor: QRect) -> None:
        self.setText(text)
        self.adjustSize()
        self.place(anchor)
        self.show()
        self._timer.start(HINT_MS)  # 再次顯示時重新計時

    def place(self, anchor: QRect) -> None:
        """放在桌寵正上方（上方放不下就放下方），水平置中並夾在螢幕內。"""
        screen = (QApplication.screenAt(anchor.center()) or QApplication.primaryScreen()).availableGeometry()
        x = anchor.center().x() - self.width() // 2
        y = anchor.top() - self.GAP - self.height()
        if y < screen.top():
            y = anchor.bottom() + self.GAP
        x = max(screen.left(), min(x, screen.right() - self.width() + 1))
        y = max(screen.top(), min(y, screen.bottom() - self.height() + 1))
        self.move(x, y)


class PetWindow(QWidget):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.sessions: list[Session] = []
        self._cache: dict = {}
        self._signature = None
        self._last_states: dict[str, str] | None = None  # None = 尚未讀過，第一次不發通知
        self._drag_offset = QPoint()
        self._press_global = QPoint()
        self._pressed = False
        self._dragged = False
        self._wolf_rect = QRect()
        self._hits: list[tuple[QRect, Session | None]] = []
        self._tray: QSystemTrayIcon | None = None
        self._tray_state = None
        self._jumper = JumpRunner(self)
        self._jumper.finished.connect(self._on_jump_finished)
        self._last_jump: wt_jump.JumpResult | None = None
        self._hint = JumpHint(self)
        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self._jumper.cancel)  # 桌寵關閉：不再開始新的切換動作

        # 無邊框 + 永遠置頂 + Tool（避免出現在工作列）
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._font = QFont()
        self._font.setPointSize(9)
        self._emoji_font = QFont()
        self._emoji_font.setPointSize(36)

        # 預先載入小狼圖（縮到顯示尺寸）；缺檔則改用 emoji
        self._pixmaps = {}
        for s, path in WOLF_IMG.items():
            if path.exists():
                self._pixmaps[s] = QPixmap(str(path)).scaled(
                    ANIMAL_SIZE, ANIMAL_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # 監看 sessions 資料夾：session 檔案會一直增減，只監看目錄本身就夠，
        # 目錄事件（新增/刪除/覆寫其中檔案）在 Windows 上比逐檔監看穩定。
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self._watcher = QFileSystemWatcher(self)
        self._watcher.addPath(str(SESSIONS_DIR))
        self._watcher.directoryChanged.connect(self._on_dir_changed)

        # 備援輪詢：負責逾時判定、經過時間更新、waiting 閃爍，也兜住監看漏掉的變動
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(POLL_MS)

        self._sync_tray()
        self.refresh()

    # ---- 讀取與刷新 ----
    def _on_dir_changed(self, _path):
        # 目錄監看在部分情況下會被系統移除，補回監看清單
        if str(SESSIONS_DIR) not in self._watcher.directories():
            self._watcher.addPath(str(SESSIONS_DIR))
        self.refresh()
        # 事件可能在寫入完成前就觸發，稍後再讀一次確保拿到完整內容
        QTimer.singleShot(100, self.refresh)

    def refresh(self):
        now = time.time()
        self.sessions = load_sessions(now, self._cache)
        self._notify_transitions()

        texts = tuple(session_text(s, now) for s in self.sessions) if self.config["show_labels"] else ()
        signature = (self.config["theme"], self.config["show_labels"],
                     tuple((s.sid, s.state, s.label) for s in self.sessions), texts)
        if signature != self._signature:
            self._signature = signature
            self._relayout()
            self.update()
            self._update_tray()
        elif any(s.state == "waiting" for s in self.sessions):
            self.update()  # waiting 閃爍

    def _notify_transitions(self):
        current = {s.sid: s.state for s in self.sessions}
        previous = self._last_states
        self._last_states = current
        if previous is None or not (self.config["notify"] and self._tray):
            return
        for s in self.sessions:
            if s.state == previous.get(s.sid):
                continue
            if s.state == "waiting":
                self._tray.showMessage(f"{s.label} 需要你處理", "等待批准或回答",
                                       QSystemTrayIcon.Warning, 8000)
            elif s.state == "done":
                self._tray.showMessage(f"{s.label} 已完成", "換你了",
                                       QSystemTrayIcon.Information, 5000)

    # ---- 版面配置 ----
    def _relayout(self):
        animal = self.config["theme"] == "animal"
        labels = self.config["show_labels"]
        fm = QFontMetrics(self._font)
        now = time.time()
        hits = []

        # 要畫的 session；紅綠燈版沒有任何 session 時留一顆灰燈當作「還活著」的提示
        items: list[Session | None] = list(self.sessions)
        if not items and not animal:
            items = [None]
        # 動物版只有一個 session 時，小狼本身就表達了狀態，不另外畫圓點
        if animal and not labels and len(items) < 2:
            items = []

        top = MARGIN
        width = 0
        if animal:
            top += ANIMAL_SIZE
            width = ANIMAL_SIZE + MARGIN * 2

        if labels and items:
            rows = []
            row_w = 0
            for s in items:
                text = session_text(s, now) if s else "沒有 session"
                w = ROW_PAD * 2 + ROW_DIAMETER + 6 + fm.horizontalAdvance(text)
                rows.append((s, w))
                row_w = max(row_w, w)
            width = max(width, row_w + MARGIN * 2)
            y = top + (4 if animal else 0)
            for s, _w in rows:
                hits.append((QRect((width - row_w) // 2, y, row_w, ROW_HEIGHT), s))
                y += ROW_HEIGHT + 2
            height = y + MARGIN
        elif items:
            d = STRIP_DIAMETER if animal else LIGHT_DIAMETER
            strip_w = len(items) * d + (len(items) - 1) * DOT_GAP
            width = max(width, strip_w + MARGIN * 2)
            y = top + (4 if animal else 0)
            x = (width - strip_w) // 2
            for s in items:
                hits.append((QRect(x, y, d, d), s))
                x += d + DOT_GAP
            height = y + d + MARGIN
        else:
            height = top + MARGIN

        self._wolf_rect = QRect((width - ANIMAL_SIZE) // 2, MARGIN, ANIMAL_SIZE, ANIMAL_SIZE) \
            if animal else QRect()
        self._hits = hits
        self._resize_anchored(width, height)

    def _resize_anchored(self, w: int, h: int):
        """改變大小時，固定住離螢幕邊緣最近的那個角，視窗才不會長出螢幕外。"""
        if self.size() == QSize(w, h):
            return
        g = self.geometry()
        screen = (self.screen() or QApplication.primaryScreen()).availableGeometry()
        x = g.right() - w + 1 if g.center().x() > screen.center().x() else g.x()
        y = g.bottom() - h + 1 if g.center().y() > screen.center().y() else g.y()
        self.setFixedSize(w, h)
        if self.isVisible():
            self.move(x, y)

    # ---- 繪製 ----
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        blink_dim = int(time.time() * 2) % 2 == 1

        if self.config["theme"] == "animal":
            state = aggregate_state(self.sessions)
            pm = self._pixmaps.get(state)
            if pm:
                p.drawPixmap(self._wolf_rect.x() + (ANIMAL_SIZE - pm.width()) // 2,
                             self._wolf_rect.y() + (ANIMAL_SIZE - pm.height()) // 2, pm)
            else:
                p.setFont(self._emoji_font)
                p.drawText(self._wolf_rect, Qt.AlignCenter, STATE_ART[state])

        now = time.time()
        p.setFont(self._font)
        for rect, s in self._hits:
            state = s.state if s else "idle"
            color = QColor(STATE_COLORS[state])
            if state == "waiting" and blink_dim:
                color.setAlpha(110)
            if self.config["show_labels"]:
                # 半透明深色底，任何桌布上都讀得到字
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(30, 30, 30, 200))
                p.drawRoundedRect(rect, 6, 6)
                dot = QRect(rect.x() + ROW_PAD, rect.y() + (rect.height() - ROW_DIAMETER) // 2,
                            ROW_DIAMETER, ROW_DIAMETER)
                p.setPen(QPen(QColor(0, 0, 0, 90), 1))
                p.setBrush(QBrush(color))
                p.drawEllipse(dot)
                p.setPen(QColor("#f0f0f0"))
                text_rect = rect.adjusted(ROW_PAD + ROW_DIAMETER + 6, 0, -ROW_PAD, 0)
                p.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft,
                           session_text(s, now) if s else "沒有 session")
            else:
                p.setPen(QPen(QColor(0, 0, 0, 90), 2))  # 淡黑外框，任何底色都看得到
                p.setBrush(QBrush(color))
                p.drawEllipse(rect.adjusted(1, 1, -1, -1))

    # ---- 滑鼠停留：顯示該 session 詳細 ----
    def event(self, e):
        if e.type() == e.Type.ToolTip:
            pos = e.pos()
            tip = None
            for rect, s in self._hits:
                if rect.contains(pos) and s:
                    tip = self._session_tooltip(s)
                    break
            if tip is None and self._wolf_rect.contains(pos):
                tip = self._summary_tooltip()
            if tip:
                QToolTip.showText(e.globalPos(), tip, self)
            else:
                QToolTip.hideText()
            return True
        return super().event(e)

    def _session_tooltip(self, s: Session) -> str:
        now = time.time()
        lines = [s.label, f"{STATE_LABEL[s.state]}（{format_elapsed(now - s.since)}）"]
        if s.cwd:
            lines.append(s.cwd)
        return "\n".join(lines)

    def _summary_tooltip(self) -> str:
        if not self.sessions:
            return "目前沒有 Claude Code session"
        now = time.time()
        return "\n".join(session_text(s, now) for s in self.sessions)

    # ---- 拖曳與點一下 ----
    # 左鍵按下到放開之間，移動距離超過系統拖曳門檻（QApplication.startDragDistance()）才算拖曳：
    # 移動桌寵並記住位置。未超過門檻算「點一下」：桌寵不動、不記位置，點在圓點／清單列上才跳轉。
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._drag_offset = self._press_global - self.frameGeometry().topLeft()
            self._pressed = True
            self._dragged = False
            event.accept()

    def mouseMoveEvent(self, event):
        if self._pressed and event.buttons() & Qt.LeftButton:
            pos = event.globalPosition().toPoint()
            if not self._dragged:
                if (pos - self._press_global).manhattanLength() <= QApplication.startDragDistance():
                    return  # 還沒超過門檻：可能只是點一下時手抖，不移動
                self._dragged = True
            self.move(pos - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self._pressed:
            return
        self._pressed = False
        if self._dragged:
            self.config["pos"] = [self.x(), self.y()]
            save_config(self.config)
        else:
            self._on_click(event.position().toPoint())

    def _on_click(self, pos: QPoint):
        """點一下：紅綠燈版點在 session 的圓點或清單列上就切到它的終端機，其他位置沒有反應。"""
        if self.config["theme"] != "light" or not wt_jump.supported():
            return  # 動物版點擊另行處理；非 Windows 不動作、不出提示
        for rect, s in self._hits:
            if rect.contains(pos):
                if s:  # 沒有 session 時那顆灰點（s 為 None）點了沒反應
                    self._jump_to(s.transcript)
                return

    def moveEvent(self, event):
        super().moveEvent(event)
        if self._hint.isVisible():
            self._hint.place(self.frameGeometry())  # 提示顯示中拖曳桌寵，提示跟著走

    # ---- 右鍵選單（桌寵與系統匣共用） ----
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        self._populate_menu(menu)
        menu.exec(event.globalPos())

    def _populate_menu(self, menu: QMenu):
        menu.clear()
        now = time.time()
        if self.sessions:
            for s in self.sessions:
                sub = menu.addMenu(QIcon(dot_pixmap(s.state)), session_text(s, now))
                if wt_jump.supported():
                    sub.addAction("切換到終端機", lambda t=s.transcript: self._jump_to(t))
                if s.cwd:
                    sub.addAction("開啟資料夾", lambda c=s.cwd: QDesktopServices.openUrl(
                        QUrl.fromLocalFile(c)))
                sub.addAction("從清單移除", lambda sid=s.sid: self._remove_session(sid))
            menu.addAction("清除閒置的 session", self._clear_idle)
        else:
            menu.addAction("目前沒有 Claude Code session").setEnabled(False)
        menu.addSeparator()

        theme_menu = menu.addMenu("外觀")
        group = QActionGroup(theme_menu)
        for key, name in (("animal", "動物版"), ("light", "紅綠燈版")):
            act = QAction(name, theme_menu, checkable=True, checked=self.config["theme"] == key)
            act.triggered.connect(lambda _=False, k=key: self._set_option("theme", k))
            group.addAction(act)
            theme_menu.addAction(act)

        self._add_toggle(menu, "顯示專案名稱", "show_labels")
        notify = self._add_toggle(menu, "桌面通知（需要你／完成時）", "notify")
        notify.setEnabled(QSystemTrayIcon.isSystemTrayAvailable())
        if autostart_supported():
            act = menu.addAction("開機自動啟動")
            act.setCheckable(True)
            act.setChecked(autostart_enabled())
            act.toggled.connect(set_autostart)
        menu.addSeparator()
        menu.addAction("關閉桌寵", QApplication.quit)

    def _add_toggle(self, menu: QMenu, text: str, key: str) -> QAction:
        act = menu.addAction(text)
        act.setCheckable(True)
        act.setChecked(bool(self.config[key]))
        act.toggled.connect(lambda checked: self._set_option(key, checked))
        return act

    def _set_option(self, key: str, value):
        self.config[key] = value
        save_config(self.config)
        if key == "notify":
            self._sync_tray()
        self.refresh()

    def _remove_session(self, sid: str):
        try:
            (SESSIONS_DIR / f"{sid}.json").unlink()
        except OSError:
            pass
        self.refresh()

    # ---- 切換到終端機 ----
    def _jump_to(self, transcript: str):
        """所有跳轉入口（右鍵選單、點圓點、點小狼）都走這裡。"""
        if self._jumper.busy:
            return  # 同一時間只處理一個跳轉：處理中再觸發直接忽略，不出現提示
        self._jumper.start(transcript)

    def _on_jump_finished(self, result):
        self._last_jump = result
        text = jump_hint_text(result)
        if text:
            self._hint.show_near(text, self.frameGeometry())

    def _clear_idle(self):
        for s in self.sessions:
            if s.state == "idle":
                self._remove_session(s.sid)

    # ---- 系統匣（只有開啟桌面通知時才出現，Windows toast 需要它） ----
    def _sync_tray(self):
        want = bool(self.config["notify"]) and QSystemTrayIcon.isSystemTrayAvailable()
        if want and not self._tray:
            self._tray = QSystemTrayIcon(self)
            self._tray_menu = QMenu()
            self._tray_menu.aboutToShow.connect(lambda: self._populate_menu(self._tray_menu))
            self._tray.setContextMenu(self._tray_menu)
            self._tray_state = None
            self._update_tray()
            self._tray.show()
        elif not want and self._tray:
            self._tray.hide()
            self._tray.deleteLater()
            self._tray = None

    def _update_tray(self):
        if not self._tray:
            return
        state = aggregate_state(self.sessions)
        if state != self._tray_state:
            self._tray_state = state
            self._tray.setIcon(QIcon(dot_pixmap(state)))
        self._tray.setToolTip("TerminalPet\n" + self._summary_tooltip())


def initial_position(pet: PetWindow, app: QApplication) -> QPoint:
    pos = pet.config.get("pos")
    if isinstance(pos, list) and len(pos) == 2:
        point = QPoint(int(pos[0]), int(pos[1]))
        # 上次的位置可能在已拔掉的外接螢幕上，確認還看得到才沿用
        rect = QRect(point, pet.size())
        if any(sc.availableGeometry().intersects(rect) for sc in app.screens()):
            return point
    screen = app.primaryScreen().availableGeometry()
    return QPoint(screen.right() - pet.width() - 40, screen.bottom() - pet.height() - 40)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    app.setApplicationName("TerminalPet")

    # 單一執行個體：重複開啟只會疊出兩隻一模一樣的桌寵
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(LOCK_FILE))
    if not lock.tryLock(100):
        QMessageBox.information(None, "TerminalPet",
                                "桌寵已經在執行中。\n要切換外觀請在桌寵上按右鍵 →「外觀」。")
        return

    config = load_config()
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ("light", "office"):
            config["theme"] = "light"
        elif arg in ("animal", "pet", "wolf"):
            config["theme"] = "animal"
        save_config(config)

    pet = PetWindow(config)
    pet.move(initial_position(pet, app))
    pet.show()
    app.exec()
    lock.unlock()


if __name__ == "__main__":
    main()
