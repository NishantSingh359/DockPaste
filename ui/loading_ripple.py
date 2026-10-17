"""Small accent-colored ripple indicator for asynchronous clip loading."""

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class LoadingRipple(QWidget):
    def __init__(self, color="#007AFF", size=42, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._phase = 0.0
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAccessibleName("Loading clips")
        self._timer = QTimer(self)
        self._timer.setInterval(20)
        self._timer.timeout.connect(self._advance)

    def set_color(self, color):
        self._color = QColor(color)
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self._timer.start()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def _advance(self):
        self._phase = (self._phase + 0.016) % 1.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = self.rect().center()
        max_radius = min(self.width(), self.height()) / 2 - 2

        for offset in (0.0, 0.5):
            phase = (self._phase + offset) % 1.0
            color = QColor(self._color)
            color.setAlphaF(0.62 * (1.0 - phase))
            pen = QPen(color, max(1.0, 2.2 - phase * 1.1))
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            radius = 3.0 + phase * (max_radius - 3.0)
            painter.drawEllipse(center, round(radius), round(radius))
