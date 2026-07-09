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

from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QAction, QFont, QPainter, QColor, QBrush, QPen
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QWidget, QVBoxLayout

STATE_FILE = Path.home() / ".terminalpet" / "state.json"

# 讀取間隔（毫秒）
POLL_MS = 500
# 超過這麼多秒沒有新狀態，就當作睡著
IDLE_TIMEOUT_SEC = 120
DEFAULT_STATE = "sleeping"

# ---- 動物版：各狀態的佔位表情（之後換成 GIF 路徑）----
STATE_ART = {
    "thinking": "🦀💭",
    "working": "🦀⚙️",
    "waiting": "🦀❗",
    "done": "🦀✅",
    "sleeping": "🦀💤",
}

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
            self.label = QLabel(STATE_ART[DEFAULT_STATE])
            self.label.setAlignment(Qt.AlignCenter)
            font = QFont()
            font.setPointSize(36)
            self.label.setFont(font)
            layout.addWidget(self.label)

        # 定時輪詢狀態檔
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_state)
        self.timer.start(POLL_MS)
        self.refresh_state()

    # ---- 狀態讀取 ----
    def read_state(self) -> str:
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            state = data.get("state", DEFAULT_STATE)
            ts = data.get("ts", 0)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return DEFAULT_STATE
        if time.time() - ts > IDLE_TIMEOUT_SEC:
            return "sleeping"
        return state if state in STATE_ART else DEFAULT_STATE

    def refresh_state(self):
        state = self.read_state()
        if state == self._current_state:
            return
        self._current_state = state
        if self.theme == "light":
            self.update()  # 觸發 paintEvent 重畫圓點
        else:
            self.label.setText(STATE_ART[state])
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
