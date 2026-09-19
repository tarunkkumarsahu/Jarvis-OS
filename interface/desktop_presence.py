"""Lightweight persistent desktop entrypoints for the existing JARVIS app.

The tray is available only when the OS actually supports it. A hidden main
window continues to own the AI/runtime; an explicit Quit performs shutdown.
"""
import math

from PySide6.QtCore import QObject, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLineEdit, QMenu,
    QPushButton, QSystemTrayIcon, QVBoxLayout, QWidget,
)


def jarvis_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor("#50dce9"), 2))
    painter.setBrush(QColor("#102b3a"))
    painter.drawEllipse(5, 5, 54, 54)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#72e8f7"))
    painter.drawEllipse(23, 23, 18, 18)
    painter.end()
    return QIcon(pixmap)


class QuickCommand(QDialog):
    submitted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ask JARVIS")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(510)
        self.setStyleSheet(
            "QDialog { background: #0d141c; color: #f3f7fa; }"
            "QLineEdit { background: #101f2a; color: #f3f7fa; border: 1px solid #36717c;"
            " border-radius: 10px; padding: 12px; font-size: 16px; }"
            "QPushButton { background: #163842; color: #e1fbff; border-radius: 9px;"
            " padding: 12px; }"
        )
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask JARVIS or continue your project…")
        self.input.returnPressed.connect(self.submit)
        send = QPushButton("Run")
        send.clicked.connect(self.submit)
        row.addWidget(self.input, 1)
        row.addWidget(send)
        layout.addLayout(row)

    def submit(self):
        command = self.input.text().strip()
        if not command:
            return
        self.input.clear()
        self.submitted.emit(command)
        self.accept()


class FloatingOrb(QWidget):
    activated = Signal()

    def __init__(self):
        super().__init__(
            None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(70, 70)
        self.setToolTip("Open JARVIS")
        self._phase = 0.0
        self._drag_offset = None
        self._dragged = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(75)

    def park(self):
        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(area.right() - self.width() - 18,
                      area.bottom() - self.height() - 95)

    def _tick(self):
        if not self.isVisible():
            return
        self._phase += 0.075
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        ring = QColor("#72e8f7")
        ring.setAlpha(115 + int(40 * (1 + math.sin(self._phase)) / 2))
        painter.setPen(QPen(ring, 2))
        painter.setBrush(QColor("#0b1b25"))
        painter.drawEllipse(7, 7, 56, 56)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#16414d"))
        painter.drawEllipse(17, 17, 36, 36)
        painter.setBrush(QColor("#bff7fc"))
        painter.drawEllipse(29, 29, 12, 12)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            self._dragged = False
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            position = event.globalPosition().toPoint() - self._drag_offset
            if (position - self.pos()).manhattanLength() > 3:
                self._dragged = True
            self.move(position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_offset is not None:
            self._drag_offset = None
            if not self._dragged:
                self.activated.emit()
            event.accept()


class DesktopPresence(QObject):
    """Owns tray, orb and quick command. Never starts a second JARVIS runtime."""
    show_requested = Signal()
    listen_requested = Signal()
    command_submitted = Signal(str)
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray = None
        self.orb = None
        self.quick = None

    def start(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return False
        self.tray = QSystemTrayIcon(jarvis_icon(), self)
        self.tray.setToolTip("JARVIS · Personal AI Operating Environment")
        menu = QMenu()
        menu.addAction("Open JARVIS", self.show_requested.emit)
        menu.addAction("Quick command", self.open_quick_command)
        menu.addAction("Speak to JARVIS", self.listen_requested.emit)
        menu.addSeparator()
        menu.addAction("Quit JARVIS", self.quit_requested.emit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()
        self.orb = FloatingOrb()
        self.orb.activated.connect(self.show_requested.emit)
        self.orb.park()
        return True

    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_requested.emit()

    def show_orb(self):
        if self.orb:
            self.orb.show()
            self.orb.raise_()

    def hide_orb(self):
        if self.orb:
            self.orb.hide()

    def open_quick_command(self):
        if self.quick is None:
            self.quick = QuickCommand()
            self.quick.submitted.connect(self.command_submitted.emit)
        self.quick.show()
        self.quick.raise_()
        self.quick.activateWindow()
        self.quick.input.setFocus()

    def shutdown(self):
        if self.quick:
            self.quick.close()
        if self.orb:
            self.orb.close()
        if self.tray:
            self.tray.hide()
