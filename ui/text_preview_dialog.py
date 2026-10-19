from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QApplication, QDialog, QPlainTextEdit, QVBoxLayout

from config import APP_NAME
from utils.app_icon import create_app_icon
import ui_config


class TextPreviewDialog(QDialog):
    """A read-only, theme-aware window sized to fit a text clipboard item."""

    def __init__(self, text, theme, available_geometry=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(APP_NAME)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        # The shelf is a topmost, non-activating tool window. Keep its preview
        # above the shelf so it cannot open hidden behind the click source.
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowIcon(create_app_icon())

        self.preview = QPlainTextEdit(self)
        self.preview.setReadOnly(True)
        self.preview.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.preview.setPlainText(text)

        layout = QVBoxLayout(self)
        layout.addWidget(self.preview)
        self._layout = layout
        self.set_theme(theme)

        available_geometry = available_geometry or self._primary_available_geometry()
        layout_config = ui_config.TEXT_PREVIEW
        max_width = max(
            layout_config["max_min_width"],
            int(available_geometry.width() * layout_config["max_width_ratio"]),
        )
        max_height = max(
            layout_config["max_min_height"],
            int(available_geometry.height() * layout_config["max_height_ratio"]),
        )
        metrics = QFontMetrics(self.preview.font())
        sample = text[: layout_config["measurement_sample_length"]]
        longest_sample_line = max((len(line) for line in sample.splitlines()), default=0)
        columns = max(
            layout_config["measurement_min_columns"],
            min(longest_sample_line, layout_config["measurement_max_columns"]),
        )
        line_count = max(1, text.count("\n") + 1)
        desired_width = (
            metrics.horizontalAdvance("M" * columns)
            + layout_config["horizontal_padding_allowance"]
        )
        desired_height = (
            min(line_count, layout_config["measurement_max_lines"])
            * metrics.lineSpacing()
        ) + layout_config["vertical_padding_allowance"]
        width = min(max_width, max(layout_config["min_width"], desired_width))
        height = min(max_height, max(layout_config["min_height"], desired_height))
        self.resize(width, height)
        self.move(
            available_geometry.center().x() - width // 2,
            available_geometry.center().y() - height // 2,
        )

    def set_theme(self, theme):
        preview_theme = (theme or {}).get("text_preview", {})
        background = preview_theme.get("background", "#202124")
        foreground = preview_theme.get("text", "#e5e7eb")
        accent = preview_theme.get("selection", "#5677c8")
        font_size = int(preview_theme.get("font_size", 13))
        font_family = preview_theme.get("font_family", "Segoe UI")
        self._layout.setContentsMargins(*preview_theme.get("padding", [12, 12, 12, 12]))
        self.preview.setFont(QFont(font_family, font_size))
        self.setStyleSheet(f"""
            QDialog {{ background: {background}; color: {foreground}; }}
            QPlainTextEdit {{
                background: {background};
                color: {foreground};
                border: none;
                selection-background-color: {accent};
                padding: {int(preview_theme.get("text_padding", 8))}px;
            }}
        """)

    @staticmethod
    def _primary_available_geometry():
        screen = QApplication.primaryScreen()
        if screen is not None:
            return screen.availableGeometry()
        return QRect(0, 0, 1024, 768)
