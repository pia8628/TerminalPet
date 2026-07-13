"""TerminalPet — 監看 Claude Code 狀態的桌面小工具。

一個透明、無邊框、永遠置頂的小視窗，定時讀取狀態檔，
依 Claude Code 目前的狀態切換外觀。可用滑鼠拖曳，右鍵選單可關閉。

兩種外觀（用啟動參數切換）：
    python pet.py            動物版（emoji 佔位，之後換成螃蟹／小狼 GIF）
    python pet.py light      辦公室紅綠燈版（小圓點，低調、掃一眼就懂）
"""

import json
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPoint, QFileSystemWatcher
from PySide6.QtGui import QAction, QFont, QPainter, QColor, QBrush, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QWidget, QVBoxLayout

STATE_DIR = Path.home() / ".terminalpet"
# 每個 Claude Code session 各寫一個狀態檔到這個資料夾（由 pet-state.sh 寫入）。
SESSIONS_DIR = STATE_DIR / "sessions"
# 舊版單一狀態檔，sessions/ 為空時作為回退來源，方便平滑升級。
LEGACY_STATE_FILE = STATE_DIR / "state.json"
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

# 輪詢間隔（毫秒）。Windows 的 QFileSystemWatcher 對「檔案覆寫」偵測不可靠，
# 實務上是靠這個輪詢兜底，所以間隔就是使用者感受到的最壞延遲，設短一點。
POLL_MS = 250
# 超過這麼多秒沒有新狀態，就當作該 session 睡著
IDLE_TIMEOUT_SEC = 120
# 超過這麼久沒更新的 session 檔視為過期，直接清掉，避免累積
SESSION_STALE_SEC = 3600
DEFAULT_STATE = "sleeping"

# 多 session 聚合時的優先級：數字越大越優先顯示。
# 「需要你介入（waiting）」永遠蓋過其他狀態，才不會漏看要核准的 session。
STATE_PRIORITY = {
    "waiting": 4,
    "working": 3,
    "thinking": 2,
    "done": 1,
    "sleeping": 0,
}

# ---- 動物版：小狼圖檔（在 assets/），找不到檔案時退回 emoji 佔位 ----
STATE_IMG = {s: ASSETS_DIR / f"wolf_{s}.png"
             for s in ("thinking", "working", "waiting", "done", "sleeping")}
STATE_ART = {
    "thinking": "🦀💭",
    "working": "🦀⚙️",
    "waiting": "🦀❗",
    "done": "🦀✅",
    "sleeping": "🦀💤",
}
ANIMAL_SIZE = 120  # 小狼顯示邊長（px）

# ---- 辦公室紅綠燈版：各狀態的顏色 ----
STATE_COLORS = {
    "thinking": "#f5c518",  # 黃：思考／處理中
    "working": "#2ecc71",   # 綠：自己在跑
    "waiting": "#e74c3c",   # 紅：需要你介入
    "done": "#2ecc71",      # 綠：完成
    "sleeping": "#7f8c8d",  # 灰：閒置
}
LIGHT_DIAMETER = 24  # 圓點直徑（px），要更小改這裡
LIGHT_MARGIN = 3     # 圓點外框留白


class PetWindow(QWidget):
    def __init__(self, theme="animal"):
        super().__init__()
        self.theme = theme
        self._current_state = None
        self._drag_offset = QPoint()

        # 無邊框 + 永遠置頂 + Tool（避免出現在工作列）
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        if self.theme == "light":
            size = LIGHT_DIAMETER + LIGHT_MARGIN * 2
            self.setFixedSize(size, size)
            self.label = None
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            self.label = QLabel()
            self.label.setAlignment(Qt.AlignCenter)
            font = QFont()
            font.setPointSize(36)
            self.label.setFont(font)
            layout.addWidget(self.label)
            # 預先載入小狼圖（縮到顯示尺寸）；缺檔則留空，改用 emoji
            self._pixmaps = {}
            for s, path in STATE_IMG.items():
                if path.exists():
                    pm = QPixmap(str(path)).scaled(
                        ANIMAL_SIZE, ANIMAL_SIZE,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation,
                    )
                    self._pixmaps[s] = pm

        # 監看 sessions 資料夾：session 檔案會一直增減，只監看目錄本身就夠，
        # 目錄事件（新增/刪除/覆寫其中檔案）在 Windows 上比逐檔監看穩定。
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self._watcher = QFileSystemWatcher(self)
        self._watcher.addPath(str(SESSIONS_DIR))
        self._watcher.directoryChanged.connect(self._on_state_file_changed)

        # 備援輪詢：負責睡眠逾時判定，也兜住監看漏掉的變動
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_state)
        self.timer.start(POLL_MS)
        self.refresh_state()

    def _on_state_file_changed(self, _path):
        # 目錄監看在部分情況下會被系統移除，補回監看清單
        if str(SESSIONS_DIR) not in self._watcher.directories():
            self._watcher.addPath(str(SESSIONS_DIR))
        self.refresh_state()
        # 事件可能在寫入完成前就觸發，稍後再讀一次確保拿到完整內容
        QTimer.singleShot(100, self.refresh_state)

    # ---- 單一 session 檔讀取（回傳 None 代表讀不到/正在寫入，呼叫端應忽略） ----
    @staticmethod
    def _read_session_file(path: Path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        state = data.get("state", DEFAULT_STATE)
        ts = data.get("ts", 0)
        if state not in STATE_PRIORITY:
            state = DEFAULT_STATE
        return state, ts

    # ---- 狀態讀取：掃全部 session 檔，取優先級最高者 ----
    def read_state(self) -> str | None:
        now = time.time()
        best_state = None
        best_priority = -1
        any_session = False

        if SESSIONS_DIR.exists():
            for path in SESSIONS_DIR.glob("*.json"):
                parsed = self._read_session_file(path)
                if parsed is None:
                    continue
                state, ts = parsed
                age = now - ts
                if age > SESSION_STALE_SEC:
                    # 早就沒在跑的 session，清掉避免資料夾一直長大
                    try:
                        path.unlink()
                    except OSError:
                        pass
                    continue
                any_session = True
                if age > IDLE_TIMEOUT_SEC:
                    state = "sleeping"
                priority = STATE_PRIORITY[state]
                if priority > best_priority:
                    best_priority = priority
                    best_state = state

        if any_session:
            return best_state

        # 沒有任何 session 檔：回退舊版單一狀態檔，方便從舊版平滑升級
        try:
            data = json.loads(LEGACY_STATE_FILE.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return DEFAULT_STATE
        except (json.JSONDecodeError, OSError):
            return None
        state = data.get("state", DEFAULT_STATE)
        ts = data.get("ts", 0)
        if now - ts > IDLE_TIMEOUT_SEC:
            return "sleeping"
        return state if state in STATE_ART else DEFAULT_STATE

    def refresh_state(self):
        state = self.read_state()
        if state is None or state == self._current_state:
            return
        self._current_state = state
        if self.theme == "light":
            self.update()  # 觸發 paintEvent 重畫圓點
        elif state in self._pixmaps:
            self.label.setPixmap(self._pixmaps[state])
            self.adjustSize()
        else:
            self.label.setText(STATE_ART[state])  # 缺圖退回 emoji
            self.adjustSize()

    # ---- 紅綠燈版：畫圓點 ----
    def paintEvent(self, event):
        if self.theme != "light":
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(STATE_COLORS.get(self._current_state, STATE_COLORS["sleeping"]))
        painter.setPen(QPen(QColor(0, 0, 0, 90), 2))  # 淡黑外框，任何底色都看得到
        painter.setBrush(QBrush(color))
        painter.drawEllipse(LIGHT_MARGIN, LIGHT_MARGIN, LIGHT_DIAMETER, LIGHT_DIAMETER)

    # ---- 拖曳 ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    # ---- 右鍵選單 ----
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        quit_action = QAction("關閉桌寵", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        menu.exec(event.globalPos())


def main():
    theme = "light" if len(sys.argv) > 1 and sys.argv[1].lower() in ("light", "office") else "animal"
    app = QApplication([])
    app.setQuitOnLastWindowClosed(True)
    pet = PetWindow(theme=theme)
    screen = app.primaryScreen().availableGeometry()
    if theme == "light":
        pet.move(screen.right() - 60, screen.bottom() - 60)
    else:
        pet.move(screen.right() - 160, screen.bottom() - 160)
    pet.show()
    app.exec()


if __name__ == "__main__":
    main()
