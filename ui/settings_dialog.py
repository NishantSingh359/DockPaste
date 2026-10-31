from datetime import date

from PySide6.QtCore import QEasingCurve, QPoint, QRect, Property, QPropertyAnimation, QSize, Qt, Signal, QByteArray, QUrl
from PySide6.QtGui import QDesktopServices, QColor, QFont, QFontDatabase, QIcon, QLinearGradient, QPainter, QPen
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QAbstractItemView,
    QButtonGroup,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSlider,
    QStackedWidget,
    QStyle,
    QStyleOptionSlider,
    QVBoxLayout,
    QWidget,
)

from config import (
    APP_NAME,
    APP_VERSION,
    CHIP_WIDTH_MAX_LIMIT,
    CHIP_WIDTH_MIN_LIMIT,
    CLIPBOARD_HISTORY_RETENTION_MAX_DAYS,
    CLIPBOARD_HISTORY_RETENTION_MIN_DAYS,
    SHELF_WIDTH_RATIO_MAX,
    SHELF_WIDTH_RATIO_MIN,
)
from animation_config import CHIP_SCROLL_SPEED_MIN, CHIP_SCROLL_SPEED_MAX
import ui_config as appearance
from ui.loading_ripple import LoadingRipple


class SettingsNavRow(QWidget):
    clicked = Signal()

    def __init__(self, palette, parent=None):
        super().__init__(parent)
        self._active = False
        self._hovered = False
        self._accent = QColor(palette["accent"])
        self._hover_color = QColor(palette["surface_hover"])
        self._text_color = QColor(palette["text"])

    def set_active(self, active):
        self._active = bool(active)
        self.update()

    def set_colors(self, accent, hover_color, text_color=None):
        self._accent = accent
        self._hover_color = hover_color
        if text_color is not None:
            self._text_color = text_color
        self.setStyleSheet(f"QLabel#settingsNavLabel {{ color: {self._text_color.name()}; }}")
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        if not self._active and not self._hovered:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._accent if self._active else self._hover_color)
        painter.drawRoundedRect(
            self.rect().adjusted(*appearance.NAV_ROW_INSET),
            appearance.NAV_ROW_RADIUS,
            appearance.NAV_ROW_RADIUS,
        )


class SettingsNavIcon(QWidget):
    """Consistent-size semantic line icon for a Settings section."""

    def __init__(self, icon_name, palette, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self._active = False
        self._accent = QColor(palette["accent"])
        self._selected_color = QColor(palette["white"])
        self.setFixedSize(appearance.NAV_ICON_SIZE, appearance.NAV_ICON_SIZE)

    def set_colors(self, accent, selected_color):
        self._accent = accent
        self._selected_color = selected_color
        self.update()

    def set_active(self, active):
        if self._active != bool(active):
            self._active = bool(active)
            self.update()

    def paintEvent(self, event):
        color = self._selected_color.name() if self._active else self._accent.name()
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{appearance.NAV_ICON_VIEWBOX_SIZE}" height="{appearance.NAV_ICON_VIEWBOX_SIZE}" '
            f'viewBox="0 0 {appearance.NAV_ICON_VIEWBOX_SIZE} {appearance.NAV_ICON_VIEWBOX_SIZE}" fill="none" stroke="{color}" '
            f'stroke-width="{appearance.NAV_ICON_STROKE_WIDTH}" stroke-linecap="round" stroke-linejoin="round">'
            + appearance.NAV_ICON_PATHS[self.icon_name] + '</svg>'
        )
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter, self.rect())


class ThemeOptionButton(QPushButton):
    """Theme preview swatch with a clear selected outline and label."""

    def __init__(self, theme_id, title, preview_colors, palette, parent=None):
        super().__init__(parent)
        self.theme_id = theme_id
        self._preview_colors = dict(preview_colors)
        self._text_color = QColor(palette["text"])
        self._border_color = QColor(palette["border"])
        self._accent_color = QColor(palette["accent"])
        self._surface_color = QColor(palette["surface"])
        self._hovered = False
        self._title = title
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(f"{title} theme")
        self.setFixedSize(*appearance.THEME_PICKER["option_size"])
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")

    def set_palette(self, palette, preview_colors=None):
        self._text_color = QColor(palette["text"])
        self._border_color = QColor(palette["border"])
        self._accent_color = QColor(palette["accent"])
        self._surface_color = QColor(palette["surface"])
        if preview_colors is not None:
            self._preview_colors = dict(preview_colors)
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cfg = appearance.THEME_PICKER
        option_rect = self.rect().adjusted(1, 1, -1, -1)
        outline = self._accent_color if self.isChecked() else self._border_color
        if self._hovered and not self.isChecked():
            outline = QColor(self._text_color)
            outline.setAlpha(100)
        painter.setPen(QPen(outline, 1.5 if self.isChecked() else 1))
        painter.setBrush(self._surface_color)
        painter.drawRoundedRect(option_rect, cfg["option_radius"], cfg["option_radius"])

        preview = option_rect.adjusted(
            cfg["preview_inset"],
            cfg["preview_inset"],
            -cfg["preview_inset"],
            -(option_rect.height() - cfg["preview_height"] - cfg["preview_inset"]),
        )
        preview_background = QColor(self._preview_colors.get("background", self._surface_color.name()))
        preview_surface = QColor(self._preview_colors.get("surface", self._surface_color.name()))
        preview_accent = self._accent_color
        gradient = QLinearGradient(preview.topLeft(), preview.bottomRight())
        gradient.setColorAt(0.0, preview_background)
        gradient.setColorAt(1.0, preview_surface)
        # Keep the thumbnail quiet: the theme card itself carries the outline,
        # while the preview reads as a small color sample rather than a mock UI.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(preview, cfg["preview_radius"], cfg["preview_radius"])

        inset = cfg["preview_panel_inset"]
        panel = preview.adjusted(inset, inset, -inset, -inset)
        panel.setRight(panel.right() - cfg["preview_accent_size"] // 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(preview_surface)
        painter.drawRoundedRect(panel, cfg["preview_panel_radius"], cfg["preview_panel_radius"])

        accent_size = cfg["preview_accent_size"]
        accent_tile = QRect(
            preview.right() - accent_size - 8,
            preview.bottom() - accent_size - 8,
            accent_size,
            accent_size,
        )
        painter.setPen(QPen(preview_background, 1))
        painter.setBrush(preview_accent)
        painter.drawRoundedRect(accent_tile, cfg["preview_accent_radius"], cfg["preview_accent_radius"])

        painter.setPen(self._text_color)
        font = painter.font()
        font.setFamily(appearance.FONT_FAMILY)
        font.setPointSize(cfg["option_label_size"])
        font.setWeight(QFont.Weight.DemiBold if self.isChecked() else QFont.Weight.Medium)
        painter.setFont(font)
        label_rect = option_rect.adjusted(10, cfg["preview_height"] + 10, -24, 0)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._title)
        if self.isChecked():
            badge_size = cfg["selected_badge_size"]
            badge = option_rect.adjusted(
                option_rect.width() - badge_size - 9,
                option_rect.height() - badge_size - 7,
                -9,
                -7,
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._accent_color)
            painter.drawEllipse(badge)
            painter.setPen(QPen(QColor("#FFFFFF"), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawLine(badge.left() + 3, badge.center().y(), badge.left() + 6, badge.center().y() + 3)
            painter.drawLine(badge.left() + 6, badge.center().y() + 3, badge.left() + 11, badge.center().y() - 3)


class AccentColorButton(QPushButton):
    """Circular accessible accent-color choice."""

    def __init__(self, color, palette, label, parent=None):
        super().__init__(parent)
        self.accent_color = color
        self._selection_color = QColor(palette["text"])
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._label = label
        self.setAccessibleName(f"{label} accent color")
        self.setFixedSize(*appearance.ACCENT_PICKER["option_size"])
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")

    def set_palette(self, palette):
        self._selection_color = QColor(palette["text"])
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cfg = appearance.ACCENT_PICKER
        diameter = cfg["swatch_size"]
        circle = QRect(
            (self.width() - diameter) // 2,
            cfg["swatch_top"],
            diameter,
            diameter,
        )
        if self.isChecked():
            painter.setPen(QPen(self._selection_color, cfg["border_width"]))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            ring = circle.adjusted(-2, -2, 2, 2)
            painter.drawEllipse(ring)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.accent_color))
        painter.drawEllipse(circle)
        label_font = painter.font()
        label_font.setFamily(appearance.FONT_FAMILY)
        label_font.setPointSize(cfg["label_size"])
        label_font.setWeight(QFont.Weight.DemiBold if self.isChecked() else QFont.Weight.Medium)
        painter.setFont(label_font)
        painter.setPen(self._selection_color if self.isChecked() else QColor(self._selection_color.red(), self._selection_color.green(), self._selection_color.blue(), 175))
        label_rect = self.rect().adjusted(
            0,
            cfg["swatch_top"] + diameter + cfg["label_gap"],
            0,
            0,
        )
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self._label)


class ShelfPositionButton(QPushButton):
    """Small screen preview showing where the shelf will appear."""

    def __init__(self, position, palette, parent=None):
        super().__init__(parent)
        self.position = position
        self._palette = dict(palette)
        self._hovered = False
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(f"Shelf position: {position}")
        self.setFixedSize(*appearance.SHELF_POSITION_PICKER["option_size"])
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")

    def set_palette(self, palette):
        self._palette = dict(palette)
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cfg = appearance.SHELF_POSITION_PICKER
        p = self._palette
        card = self.rect().adjusted(1, 1, -1, -1)
        outline = QColor(p["accent"] if self.isChecked() else p["border"])
        if self._hovered and not self.isChecked():
            outline = QColor(p["text"])
            outline.setAlpha(100)
        painter.setPen(QPen(outline, 1.5 if self.isChecked() else 1))
        painter.setBrush(QColor(p["surface"]))
        painter.drawRoundedRect(card, cfg["option_radius"], cfg["option_radius"])

        preview = card.adjusted(
            cfg["preview_inset"], cfg["preview_inset"],
            -cfg["preview_inset"],
            -(card.height() - cfg["preview_height"] - cfg["preview_inset"]),
        )
        gradient = QLinearGradient(preview.topLeft(), preview.bottomRight())
        gradient.setColorAt(0.0, QColor(p["background"]))
        gradient.setColorAt(1.0, QColor(p["surface_hover"]))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(preview, cfg["preview_radius"], cfg["preview_radius"])

        screen = preview.adjusted(cfg["screen_inset"], 8, -cfg["screen_inset"], -8)
        painter.setBrush(QColor(p["surface"]))
        painter.drawRoundedRect(screen, cfg["screen_radius"], cfg["screen_radius"])

        # A single accent shelf marker keeps the preview legible and consistent
        # with the compact color samples used by the theme picker.
        shelf_width = min(cfg["shelf_width"], screen.width() - 16)
        shelf_height = cfg["shelf_height"]
        shelf_y = screen.top() + 5 if self.position == "Top" else screen.bottom() - shelf_height - 5
        shelf = QRect(screen.center().x() - shelf_width // 2, shelf_y, shelf_width, shelf_height)
        painter.setBrush(QColor(p["accent"]))
        painter.drawRoundedRect(shelf, cfg["shelf_radius"], cfg["shelf_radius"])

        label = card.adjusted(10, cfg["preview_height"] + 10, -24, 0)
        painter.setPen(QColor(p["text"]))
        font = painter.font()
        font.setFamily(appearance.FONT_FAMILY)
        font.setPointSize(cfg["label_size"])
        font.setWeight(QFont.Weight.DemiBold if self.isChecked() else QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(label, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.position)

        if self.isChecked():
            badge_size = cfg["selected_badge_size"]
            badge = card.adjusted(card.width() - badge_size - 9, card.height() - badge_size - 7, -9, -7)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(p["accent"]))
            painter.drawEllipse(badge)
            painter.setPen(QPen(QColor(p["white"]), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawLine(badge.left() + 3, badge.center().y(), badge.left() + 6, badge.center().y() + 3)
            painter.drawLine(badge.left() + 6, badge.center().y() + 3, badge.left() + 11, badge.center().y() - 3)


class SettingsSpinBox(QSpinBox):
    """Let the settings page scroll on wheel input unless editing this value."""

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
            return
        super().wheelEvent(event)


class SettingsDoubleSpinBox(QDoubleSpinBox):
    """Avoid changing numeric settings accidentally while scrolling the page."""

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
            return
        super().wheelEvent(event)


class HistoryDateSlider(QSlider):
    """Discrete date slider with a visible marker for every available date."""

    def __init__(self, palette, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._date_palette = palette

    def set_palette(self, palette):
        self._date_palette = palette
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        groove = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, option,
            QStyle.SubControl.SC_SliderGroove, self,
        )
        handle = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, option,
            QStyle.SubControl.SC_SliderHandle, self,
        )
        left = groove.left() + handle.width() / 2
        right = groove.right() - handle.width() / 2
        if right <= left:
            return
        center_y = groove.center().y()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(self._date_palette["secondary_text"]), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPoint(round(left), center_y), QPoint(round(right), center_y))
        painter.setPen(Qt.PenStyle.NoPen)
        span = self.maximum() - self.minimum()
        for index in range(self.minimum(), self.maximum() + 1):
            ratio = (index - self.minimum()) / span if span else 0.5
            x = left + ratio * (right - left)
            active = index == self.value()
            radius = 12 if active else 8
            color = self._date_palette["accent"] if active else self._date_palette["secondary_text"]
            painter.setBrush(QColor(color))
            painter.drawEllipse(QPoint(round(x), center_y), radius, radius)


class SettingsDialog(QDialog):
    def __init__(
        self,
        *,
        show_on_hover,
        show_on_click,
        hide_on_paste,
        highlight_shelf_on_drag,
        show_clip_type_filter,
        clip_scroll_speed,
        show_clip_indexes,
        color_preview_enabled,
        text_preview_on_double_click,
        open_images_on_double_click,
        prevent_oversize_items,
        show_oversize_warning,
        close_to_tray,
        start_with_windows,
        chip_min_width,
        chip_max_width,
        shelf_width_ratio,
        shelf_position,
        theme_name,
        available_themes,
        theme_previews,
        accent_color,
        accent_options,
        history_dates,
        selected_history_date,
        history_retention_days,
        history_loading=False,
        theme,
        on_show_on_hover,
        on_show_on_click,
        on_hide_on_paste,
        on_highlight_shelf_on_drag,
        on_show_clip_type_filter,
        on_clip_scroll_speed,
        on_show_clip_indexes,
        on_color_preview,
        on_text_preview_on_double_click,
        on_open_images_on_double_click,
        on_prevent_oversize_items,
        on_oversize_warning,
        on_close_to_tray,
        on_start_with_windows,
        on_chip_min_width,
        on_chip_max_width,
        on_shelf_width_ratio,
        on_shelf_position,
        on_history_date,
        on_history_retention_days,
        on_clear_all_history,
        on_theme,
        on_accent_color,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._theme_palette = dict(theme["settings"])
        self._accent_color = accent_color
        self._theme_previews = dict(theme_previews)
        QFontDatabase.addApplicationFont(str(appearance.FONT_FILE))
        self.resize(*appearance.WINDOW_SIZE)

        root = QHBoxLayout(self)
        root.setContentsMargins(*appearance.ROOT_MARGINS)
        root.setSpacing(appearance.ROOT_SPACING)

        self.sidebar_panel = QFrame()
        self.sidebar_panel.setObjectName("settingsControlPanel")
        self.sidebar_panel.setFixedWidth(appearance.SIDEBAR_WIDTH)
        sidebar_panel_layout = QVBoxLayout(self.sidebar_panel)
        sidebar_panel_layout.setContentsMargins(*appearance.SIDEBAR_PANEL_MARGINS)
        sidebar_panel_layout.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("settingsSidebar")
        self.sidebar.setFixedWidth(
            appearance.SIDEBAR_WIDTH - 2 * appearance.SIDEBAR_PANEL_INSET
        )
        self.sidebar.setSpacing(appearance.SIDEBAR_SPACING)
        self.sidebar.setFrameShape(QFrame.NoFrame)
        self.sidebar.setFocusPolicy(Qt.NoFocus)
        self.sidebar.setUniformItemSizes(True)
        self.sidebar.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.sidebar.verticalScrollBar().setSingleStep(appearance.SETTINGS_SCROLL_STEP)
        self.sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.pages = QStackedWidget()
        self.pages.setObjectName("settingsPages")
        self.pages.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sidebar_panel_layout.addWidget(self.sidebar)
        root.addWidget(self.sidebar_panel)
        root.addWidget(self.pages, 1)

        self._nav_rows = []
        self._nav_icons = []
        for icon_name, page_name in (
            ("general", "General"),
            ("appearance", "Appearance"),
            ("history", "History"),
            ("support", "Support"),
            ("about", "About"),
        ):
            self._add_nav_item(icon_name, page_name)
        self.sidebar.currentRowChanged.connect(self._on_nav_changed)
        self.sidebar.setCurrentRow(0)

        general = self._new_page("General", "Choose how DockPaste behaves on your desktop.")
        general_card = self._card(general)
        self.show_on_hover = self._add_switch(
            general_card, "Show Shelf on Hover", "Reveal the shelf when you move to the configured screen edge.", show_on_hover, on_show_on_hover
        )
        self.show_on_click = self._add_switch(
            general_card,
            "Show Shelf on Click",
            "Reveal the shelf when you left-click the configured screen edge.",
            show_on_click,
            on_show_on_click,
        )
        self.show_on_hover.toggled.connect(self._update_click_setting_availability)
        self._update_click_setting_availability(show_on_hover)
        self.hide_on_paste = self._add_switch(
            general_card, "Hide Shelf After Pasting", "Dismiss the shelf after you choose a clip.", hide_on_paste, on_hide_on_paste
        )
        self.highlight_shelf_on_drag = self._add_switch(
            general_card,
            "Highlight Shelf While Dragging",
            "Show the accent border when an item can be dropped on the shelf.",
            highlight_shelf_on_drag,
            on_highlight_shelf_on_drag,
        )
        self.show_clip_type_filter = self._add_switch(
            general_card,
            "Show Clip Type Filter",
            "Show the button beside the shelf to filter Text, Link, Image, and Path clips.",
            show_clip_type_filter,
            on_show_clip_type_filter,
        )
        self.close_to_tray = self._add_switch(
            general_card, "Keep Running When Closed", "Keep clipboard monitoring active from the system tray.", close_to_tray, on_close_to_tray
        )
        self.close_to_tray.setToolTip(
            "Closing the shelf hides it in the system tray and keeps clipboard monitoring active. "
            "The current history is cleared when the shelf is closed. Use Exit in the tray menu to quit."
        )
        self.start_with_windows = self._add_switch(
            general_card, "Start With Windows", "Open DockPaste automatically when you sign in.", start_with_windows, on_start_with_windows
        )
        self.text_preview_on_double_click = self._add_switch(
            general_card, "Preview Text on Double-Click", "Open a readable preview of copied text.", text_preview_on_double_click, on_text_preview_on_double_click
        )
        self.open_images_on_double_click = self._add_switch(
            general_card, "Open Images on Double-Click", "Open the copied image in your image viewer.", open_images_on_double_click, on_open_images_on_double_click
        )
        self.prevent_oversize_items = self._add_switch(
            general_card, "Skip Image Over 5 MB", "Keep large clipboard items out of local history.", prevent_oversize_items, on_prevent_oversize_items
        )
        self.oversize_warning = self._add_switch(
            general_card, "Warn When an Image Is Skipped", "Show a notice when an item exceeds the size limit.", show_oversize_warning, on_oversize_warning
        )
        self.oversize_warning.setEnabled(bool(prevent_oversize_items))
        self.prevent_oversize_items.toggled.connect(self._set_oversize_warning_availability)
        self._add_page(general)

        appearance_page = self._new_page("Appearance", "Adjust the shelf and the way clips are shown.")
        theme_card = self._card(appearance_page)
        theme_card_layout = theme_card.layout()
        theme_card_layout.setContentsMargins(*appearance.THEME_PICKER["card_margins"])
        theme_card_layout.setSpacing(appearance.THEME_PICKER["section_gap"])
        themes_heading = QLabel("Themes")
        themes_heading.setObjectName("appearanceSectionTitle")
        theme_card_layout.addWidget(themes_heading)
        themes_row = QHBoxLayout()
        themes_row.setSpacing(appearance.THEME_PICKER["row_spacing"])
        themes_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._theme_buttons = {}
        self._theme_button_group = QButtonGroup(self)
        self._theme_button_group.setExclusive(True)
        self._theme_ids_by_index = {}
        for index, (theme_id, display_name) in enumerate(available_themes):
            option = ThemeOptionButton(
                theme_id,
                display_name,
                theme_previews.get(theme_id, {}),
                self._theme_palette,
            )
            self._theme_buttons[theme_id] = option
            self._theme_ids_by_index[index] = theme_id
            self._theme_button_group.addButton(option, index)
            themes_row.addWidget(option)
        current_theme_index = next(
            (index for index, theme_id in self._theme_ids_by_index.items() if theme_id == theme_name),
            0,
        )
        if self._theme_button_group.button(current_theme_index):
            self._theme_button_group.button(current_theme_index).setChecked(True)
        self._theme_button_group.idClicked.connect(
            lambda index: on_theme(self._theme_ids_by_index[index])
        )
        theme_card_layout.addLayout(themes_row)
        theme_card_layout.addSpacing(appearance.THEME_PICKER["accent_section_gap"])
        accent_heading = QLabel("Accent Color")
        accent_heading.setObjectName("appearanceSectionTitle")
        theme_card_layout.addWidget(accent_heading)
        accents_row = QHBoxLayout()
        accents_row.setSpacing(appearance.ACCENT_PICKER["row_spacing"])
        accents_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._accent_buttons = {}
        self._accent_button_group = QButtonGroup(self)
        self._accent_button_group.setExclusive(True)
        self._accent_colors_by_index = {}
        for index, color in enumerate(accent_options):
            label = (
                appearance.ACCENT_LABELS[index]
                if index < len(appearance.ACCENT_LABELS)
                else f"Accent {index + 1}"
            )
            option = AccentColorButton(color, self._theme_palette, label)
            self._accent_buttons[color.lower()] = option
            self._accent_colors_by_index[index] = color
            self._accent_button_group.addButton(option, index)
            accents_row.addWidget(option)
        selected_accent_index = next(
            (index for index, color in self._accent_colors_by_index.items()
             if color.lower() == self._accent_color.lower()),
            0,
        )
        if self._accent_button_group.button(selected_accent_index):
            self._accent_button_group.button(selected_accent_index).setChecked(True)
        self._accent_button_group.idClicked.connect(
            lambda index: self._select_accent_color(self._accent_colors_by_index[index], on_accent_color)
        )
        theme_card_layout.addLayout(accents_row)

        shelf_position_card = self._card(appearance_page)
        shelf_position_heading = QLabel("Shelf Position")
        shelf_position_heading.setObjectName("appearanceSectionTitle")
        shelf_position_card.layout().setContentsMargins(
            *appearance.SHELF_POSITION_PICKER["card_margins"]
        )
        shelf_position_card.layout().setSpacing(
            appearance.SHELF_POSITION_PICKER["section_gap"]
        )
        shelf_position_card.layout().addWidget(shelf_position_heading)
        position_row = QHBoxLayout()
        position_row.setSpacing(appearance.SHELF_POSITION_PICKER["row_spacing"])
        position_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._shelf_position_buttons = {}
        self._shelf_position_button_group = QButtonGroup(self)
        self._shelf_position_button_group.setExclusive(True)
        self._shelf_positions_by_index = {0: "Top", 1: "Bottom"}
        for index, position in self._shelf_positions_by_index.items():
            option = ShelfPositionButton(position, self._theme_palette)
            option.setChecked(position == shelf_position)
            self._shelf_position_buttons[position] = option
            self._shelf_position_button_group.addButton(option, index)
            position_row.addWidget(option)
        self._shelf_position_button_group.idClicked.connect(
            lambda index: on_shelf_position(self._shelf_positions_by_index[index])
        )
        shelf_position_card.layout().addLayout(position_row)

        appearance_card = self._card(appearance_page)
        self.show_clip_indexes = self._add_switch(
            appearance_card, "Show Clip Indexes", "Display the keyboard index on each clip.", show_clip_indexes, on_show_clip_indexes
        )
        self.color_preview = self._add_switch(
            appearance_card, "Show Color Previews", "Show a swatch for copied color values.", color_preview_enabled, on_color_preview
        )
        self.clip_scroll_speed = self._spin(
            clip_scroll_speed,
            CHIP_SCROLL_SPEED_MIN,
            CHIP_SCROLL_SPEED_MAX,
            "×",
        )
        self.clip_scroll_speed.valueChanged.connect(on_clip_scroll_speed)
        self._add_control_row(
            appearance_card,
            "Clip Scroll Speed",
            "Adjust how far the shelf scrolls with each mouse wheel movement.",
            self.clip_scroll_speed,
        )

        sizing_card = self._card(appearance_page)
        self.chip_min_width = self._spin(chip_min_width, CHIP_WIDTH_MIN_LIMIT, CHIP_WIDTH_MAX_LIMIT, " px")
        self.chip_min_width.valueChanged.connect(on_chip_min_width)
        self._add_control_row(sizing_card, "Minimum Clip Width", "Smallest width used for a shelf clip.", self.chip_min_width)
        self.chip_max_width = self._spin(chip_max_width, CHIP_WIDTH_MIN_LIMIT, CHIP_WIDTH_MAX_LIMIT, " px")
        self.chip_max_width.valueChanged.connect(on_chip_max_width)
        self._add_control_row(sizing_card, "Maximum Clip Width", "Longest width used before clip text is shortened.", self.chip_max_width)
        self.shelf_width_ratio = SettingsDoubleSpinBox()
        self.shelf_width_ratio.setRange(SHELF_WIDTH_RATIO_MIN, SHELF_WIDTH_RATIO_MAX)
        self.shelf_width_ratio.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.shelf_width_ratio.setDecimals(appearance.SHELF_WIDTH_DECIMALS)
        self.shelf_width_ratio.setSingleStep(appearance.SHELF_WIDTH_STEP)
        self.shelf_width_ratio.setValue(shelf_width_ratio)
        self.shelf_width_ratio.valueChanged.connect(on_shelf_width_ratio)
        self._add_control_row(sizing_card, "Shelf Width", "Shelf width as a proportion of the screen.", self.shelf_width_ratio)
        self._add_page(appearance_page)

        history = self._new_page("History", "Manage saved clipboard history.")
        history_card = self._card(history)
        self.history_dates = list(history_dates) or [selected_history_date]
        date_control = QWidget()
        date_layout = QVBoxLayout(date_control)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(4)
        self.history_date_label = QLabel()
        self.history_date_label.setObjectName("browseDateValue")
        self.history_date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.history_date_slider = HistoryDateSlider(self._theme_palette)
        self.history_date_slider.setObjectName("historyDateSlider")
        self.history_date_slider.setRange(0, max(0, len(self.history_dates) - 1))
        self.history_date_slider.setTracking(True)
        selected_index = self.history_dates.index(selected_history_date) if selected_history_date in self.history_dates else 0
        self.history_date_slider.setValue(selected_index)
        self._update_history_date_label(selected_index)
        self.history_date_slider.valueChanged.connect(
            lambda index: (self._update_history_date_label(index), on_history_date(self.history_dates[index]))
        )
        date_layout.addWidget(self.history_date_label)
        date_layout.addWidget(self.history_date_slider)
        date_row = QWidget()
        date_row_layout = QVBoxLayout(date_row)
        date_row_layout.setContentsMargins(0, 18, 0, 18)
        date_row_layout.setSpacing(2)
        date_title = QLabel("Browse Copy Date")
        date_title.setObjectName("browseDateTitle")
        date_description = QLabel("Adjust slider and see the copied history.")
        date_description.setObjectName("browseDateDescription")
        date_row_layout.addWidget(date_title)
        date_row_layout.addWidget(date_description)
        date_row_layout.addSpacing(2)
        date_row_layout.addWidget(date_control)
        self._add_row(history_card, date_row)
        self.history_retention_days = self._spin(
            history_retention_days,
            CLIPBOARD_HISTORY_RETENTION_MIN_DAYS,
            CLIPBOARD_HISTORY_RETENTION_MAX_DAYS,
            " days",
        )
        self.history_retention_days.valueChanged.connect(on_history_retention_days)
        self._add_control_row(history_card, "Keep History For", "Older clips are removed automatically.", self.history_retention_days)
        self.clear_history_button = QPushButton("Clear All History")
        self.clear_history_button.setObjectName("clearHistoryButton")
        self.clear_history_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_history_button.clicked.connect(
            lambda: self._confirm_clear_history(on_clear_all_history)
        )
        self._add_control_row(
            history_card,
            "Clear All History",
            "Permanently delete every saved clip and stored image.",
            self.clear_history_button,
        )
        self.history_loading_status = QWidget()
        loading_layout = QHBoxLayout(self.history_loading_status)
        loading_layout.setContentsMargins(4, 4, 0, 4)
        loading_layout.setSpacing(10)
        self.history_loading_ripple = LoadingRipple(self._theme_palette["accent"], 28)
        loading_label = QLabel("Loading clips…")
        loading_label.setObjectName("settingDescription")
        loading_layout.addWidget(self.history_loading_ripple)
        loading_layout.addWidget(loading_label)
        loading_layout.addStretch(1)
        history.layout().addWidget(self.history_loading_status)
        self.set_history_loading(history_loading)
        self._add_page(history)

        support = self._new_page("Support", "Support DockPaste and help the project grow.")
        support_card = self._card(support)
        support_links = (
            (
                "Buy Me a Coffee",
                "Support development with a one-time contribution.",
                "https://studio.buymeacoffee.com/dashboard",
            ),
            (
                "LinkedIn",
                "Visit LinkedIn for project updates and community news.",
                "https://www.linkedin.com/in/nishantsinghinfo",
            ),
            (
                "GitHub",
                "Explore the source, report issues, or contribute code.",
                "https://github.com/NishantSingh359/DockPaste",
            ),
        )
        for title, description, url in support_links:
            link_button = QPushButton("Open")
            link_button.setObjectName("supportLinkButton")
            link_button.setCursor(Qt.CursorShape.PointingHandCursor)
            link_button.setAccessibleName(f"Open {title}")
            link_button.clicked.connect(lambda checked=False, target=url: QDesktopServices.openUrl(QUrl(target)))
            self._add_control_row(support_card, title, description, link_button)
        self._add_page(support)

        about = self._new_page("About", "App information and project details.")
        about_card = self._card(about)
        about_header = QWidget()
        about_header_layout = QHBoxLayout(about_header)
        about_header_layout.setContentsMargins(0, 4, 0, 4)
        about_header_layout.setSpacing(18)
        app_icon = QLabel()
        app_icon.setObjectName("aboutAppIcon")
        app_icon.setFixedSize(70, 70)
        app_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_icon.setPixmap(QIcon(str(appearance.APP_ICON_FILE)).pixmap(52, 52))
        about_title_column = QVBoxLayout()
        about_title_column.setContentsMargins(0, 0, 0, 0)
        about_title_column.setSpacing(6)
        app_name_label = QLabel(APP_NAME)
        app_name_label.setObjectName("aboutAppName")
        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setObjectName("aboutVersionBadge")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setFixedWidth(104)
        about_title_column.addWidget(app_name_label)
        about_title_column.addWidget(version_label, 0, Qt.AlignmentFlag.AlignLeft)
        about_header_layout.addWidget(app_icon, 0, Qt.AlignmentFlag.AlignTop)
        about_header_layout.addLayout(about_title_column, 1)
        about_card.layout().addWidget(about_header)

        description_label = QLabel(
            "Keep recent text, links, files, and images close at hand. DockPaste stores your clipboard history locally so you can quickly find and reuse what you copied."
        )
        description_label.setObjectName("settingDescription")
        description_label.setWordWrap(True)
        about_card.layout().addWidget(description_label)

        details_card = self._card(about)
        self._add_control_row(
            details_card,
            "Platform",
            "Designed for Windows desktop.",
            self._about_fact_value("Windows 10 / 11"),
        )
        self._add_control_row(
            details_card,
            "Your Data",
            "Clipboard history and settings stay on this device.",
            self._about_fact_value("Stored locally"),
        )
        source_button = QPushButton("View on GitHub")
        source_button.setObjectName("supportLinkButton")
        source_button.setCursor(Qt.CursorShape.PointingHandCursor)
        source_button.setAccessibleName("View DockPaste source on GitHub")
        source_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/NishantSingh359/DockPaste"))
        )
        self._add_control_row(
            details_card,
            "Open Source",
            "Browse the code, report an issue, or help improve DockPaste.",
            source_button,
        )
        self._add_page(about)

        self.set_theme(theme)
        self.setMaximumSize(*appearance.WINDOW_MAX_SIZE)
        primary_screen = QApplication.primaryScreen()
        if primary_screen is not None:
            available_geometry = primary_screen.availableGeometry()
            max_width = min(appearance.WINDOW_MAX_SIZE[0], available_geometry.width())
            max_height = min(appearance.WINDOW_MAX_SIZE[1], available_geometry.height())
            self.setMaximumSize(max_width, max_height)
            self.setMinimumSize(
                min(appearance.WINDOW_MIN_SIZE[0], max_width),
                min(appearance.WINDOW_MIN_SIZE[1], max_height),
            )
            self.resize(
                min(appearance.WINDOW_SIZE[0], available_geometry.width()),
                min(appearance.WINDOW_SIZE[1], available_geometry.height()),
            )
            self.move(
                available_geometry.center().x() - self.width() // 2,
                available_geometry.center().y() - self.height() // 2,
            )

    def _update_history_date_label(self, index):
        history_date = self.history_dates[index]
        try:
            history_date = date.fromisoformat(history_date).strftime("%y-%m-%d")
        except (TypeError, ValueError):
            pass
        self.history_date_label.setText(history_date)

    def _new_page(self, title, subtitle):
        page = QWidget()
        page.setObjectName("settingsPage")
        page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(*appearance.PAGE_MARGINS)
        page_layout.setSpacing(appearance.PAGE_SPACING)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        heading = QLabel(title)
        heading.setObjectName("pageHeading")
        page_layout.addWidget(heading)
        description = QLabel(subtitle)
        description.setObjectName("pageSubtitle")
        description.setWordWrap(True)
        page_layout.addWidget(description)
        page_layout.addSpacing(appearance.PAGE_DESCRIPTION_GAP)
        return page

    def _add_nav_item(self, icon_name, title):
        item = QListWidgetItem()
        item.setSizeHint(QSize(*appearance.NAV_ITEM_SIZE))
        self.sidebar.addItem(item)

        row = SettingsNavRow(self._theme_palette)
        row.setObjectName("settingsNavRow")
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(*appearance.NAV_ROW_MARGINS)
        row_layout.setSpacing(appearance.NAV_ROW_SPACING)
        icon = SettingsNavIcon(icon_name, self._theme_palette)
        icon.setObjectName("settingsNavIcon")
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        label = QLabel(title)
        label.setObjectName("settingsNavLabel")
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        label_font = QFont(
            appearance.FONT_FAMILY,
            appearance.FONT["sidebar_size"],
            appearance.FONT["sidebar_weight"],
        )
        label.setFont(label_font)
        row_layout.addWidget(icon)
        row_layout.addWidget(label, 1)
        self.sidebar.setItemWidget(item, row)
        row.clicked.connect(lambda row_index=len(self._nav_rows): self.sidebar.setCurrentRow(row_index))
        self._nav_rows.append(row)
        self._nav_icons.append(icon)

    def _on_nav_changed(self, index):
        self.pages.setCurrentIndex(index)
        for row_index, row in enumerate(self._nav_rows):
            is_active = row_index == index
            row.set_active(is_active)
            self._nav_icons[row_index].set_active(is_active)

    def _add_page(self, page):
        scroll = QScrollArea()
        scroll.setObjectName("settingsPageScroll")
        scroll.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.verticalScrollBar().setSingleStep(appearance.SETTINGS_SCROLL_STEP)
        scroll.setWidget(page)
        self.pages.addWidget(scroll)

    @staticmethod
    def _card(page):
        card = QFrame()
        card.setObjectName("settingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(*appearance.CARD_MARGINS)
        card_layout.setSpacing(appearance.CARD_ROW_SPACING)
        page.layout().addWidget(card)
        return card

    def _switch(self, title, description, checked, callback):
        checkbox = MacSwitch(self._theme_palette)
        checkbox.setObjectName("settingsSwitch")
        checkbox.setChecked(bool(checked))
        checkbox.setAccessibleName(title)
        checkbox.setToolTip(description)
        checkbox.toggled.connect(callback)
        return checkbox

    def _add_switch(self, card, title, description, checked, callback):
        checkbox = self._switch(title, description, checked, callback)
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(*appearance.SETTING_ROW_MARGINS)
        layout.setSpacing(appearance.SETTING_ROW_SPACING)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(*appearance.SETTING_TEXT_MARGINS)
        text_layout.setSpacing(appearance.SETTING_TEXT_SPACING)
        label = QLabel(title)
        label.setObjectName("settingTitle")
        detail = QLabel(description)
        detail.setObjectName("settingDescription")
        detail.setWordWrap(True)
        text_layout.addWidget(label)
        text_layout.addWidget(detail)
        layout.addLayout(text_layout, 1)
        layout.addWidget(checkbox, 0, Qt.AlignVCenter)
        self._add_row(card, row)
        return checkbox

    @staticmethod
    def _add_row(card, row):
        if card.layout().count():
            separator = QFrame()
            separator.setObjectName("rowSeparator")
            separator.setFixedHeight(appearance.ROW_SEPARATOR_HEIGHT)
            card.layout().addWidget(separator)
        card.layout().addWidget(row)

    def _add_control_row(self, card, title, description, control):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(*appearance.SETTING_ROW_MARGINS)
        layout.setSpacing(appearance.SETTING_ROW_SPACING)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(*appearance.SETTING_TEXT_MARGINS)
        text_layout.setSpacing(appearance.SETTING_TEXT_SPACING)
        label = QLabel(title)
        label.setObjectName("settingTitle")
        detail = QLabel(description)
        detail.setObjectName("settingDescription")
        detail.setWordWrap(True)
        text_layout.addWidget(label)
        text_layout.addWidget(detail)
        layout.addLayout(text_layout, 1)
        control.setMinimumWidth(appearance.CONTROL_MIN_WIDTH)
        layout.addWidget(control, 0, Qt.AlignVCenter)
        self._add_row(card, row)

    @staticmethod
    def _spin(value, minimum, maximum, suffix=""):
        spin = SettingsSpinBox()
        spin.setRange(minimum, maximum)
        spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        spin.setSuffix(suffix)
        spin.setValue(value)
        return spin

    @staticmethod
    def _about_fact_value(text):
        value = QLabel(text)
        value.setObjectName("aboutFactValue")
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return value

    def set_theme(self, theme):
        # Settings share the active theme's colors while keeping their own layout.
        p = {**self._theme_palette, **(theme or {}).get("settings", {})}
        self._theme_palette = p
        if hasattr(self, "history_date_slider"):
            self.history_date_slider.set_palette(p)
        for row in self.findChildren(SettingsNavRow):
            row.set_colors(QColor(p["accent"]), QColor(p["surface_hover"]), QColor(p["text"]))
        for icon in self.findChildren(SettingsNavIcon):
            icon.set_colors(QColor(p["accent"]), QColor(p["white"]))
        for switch in self.findChildren(MacSwitch):
            switch.set_colors(
                QColor(p["accent"]),
                QColor(p["switch_off"]),
                QColor(p["border"]),
                QColor(p["white"]),
                QColor(p["switch_disabled"]),
            )
            switch._disabled_thumb_color = QColor(p["disabled_thumb"])
        if hasattr(self, "history_loading_ripple"):
            self.history_loading_ripple.set_color(p["accent"])
        selected_theme = (theme or {}).get("name")
        for theme_id, button in self._theme_buttons.items():
            button.set_palette(p, self._theme_previews.get(theme_id, {}))
            button.setChecked(theme_id == selected_theme)
        for button in self._accent_buttons.values():
            button.set_palette(p)
        for button in self._shelf_position_buttons.values():
            button.set_palette(p)
        self.setWindowTitle(appearance.WINDOW_TITLE)
        stylesheet = appearance.settings_stylesheet(p)
        self.setStyleSheet(stylesheet)
        self.ensurePolished()
        for widget in self.findChildren(QWidget):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()
        self.update()

    def set_history_loading(self, loading):
        if hasattr(self, "history_loading_status"):
            self.history_loading_status.setVisible(bool(loading))

    def _update_click_setting_availability(self, hover_enabled):
        click_enabled = not bool(hover_enabled)
        self.show_on_click.setEnabled(click_enabled)
        self.show_on_click.setToolTip(
            "Turn off Show Shelf on Hover to configure click activation."
            if not click_enabled
            else "Reveal the shelf when you left-click the configured screen edge."
        )

    def _select_accent_color(self, color, callback):
        self._accent_color = color
        for value, button in self._accent_buttons.items():
            button.setChecked(value == color.lower())
        callback(color)

    def _set_oversize_warning_availability(self, prevention_enabled):
        self.oversize_warning.setEnabled(bool(prevention_enabled))
        if not prevention_enabled and self.oversize_warning.isChecked():
            self.oversize_warning.setChecked(False)

    def _confirm_clear_history(self, callback):
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.NoIcon)
        dialog.setWindowTitle("Clear All History")
        dialog.setText("Clear All History?")
        dialog.setInformativeText("This permanently deletes all saved clips and images.")
        cancel_button = dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        clear_button = dialog.addButton("Clear All History", QMessageBox.ButtonRole.DestructiveRole)
        clear_button.setObjectName("confirmClearButton")
        dialog.setDefaultButton(cancel_button)
        dialog.setEscapeButton(cancel_button)
        dialog.setStyleSheet(appearance.confirmation_stylesheet(self._theme_palette))
        dialog.exec()
        if dialog.clickedButton() is clear_button:
            callback()


class MacSwitch(QCheckBox):
    """Compact track-and-thumb switch drawn in the macOS settings style."""

    def __init__(self, palette, parent=None):
        super().__init__(parent)
        self._on_color = QColor(palette["accent"])
        self._off_color = QColor(palette["switch_off"])
        self._border_color = QColor(palette["border"])
        self._thumb_color = QColor(palette["white"])
        self._disabled_color = QColor(palette["switch_disabled"])
        self._disabled_thumb_color = QColor(palette["disabled_thumb"])
        self.setFixedSize(*appearance.SWITCH_SIZE)
        self._hovered = False
        self._thumb_position = float(appearance.SWITCH_THUMB_X["off"])
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._thumb_animation = QPropertyAnimation(self, b"thumbPosition", self)
        self._thumb_animation.setDuration(appearance.SWITCH_ANIMATION_MS)
        self._thumb_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate_thumb)

    def set_colors(self, on_color, off_color, border_color, thumb_color, disabled_color):
        self._on_color = on_color
        self._off_color = off_color
        self._border_color = border_color
        self._thumb_color = thumb_color
        self._disabled_color = disabled_color
        self.update()

    @Property(float)
    def thumbPosition(self):
        return self._thumb_position

    @thumbPosition.setter
    def thumbPosition(self, position):
        self._thumb_position = float(position)
        self.update()

    def _animate_thumb(self, checked):
        self._thumb_animation.stop()
        self._thumb_animation.setStartValue(self._thumb_position)
        thumb_key = "on" if checked else "off"
        self._thumb_animation.setEndValue(appearance.SWITCH_THUMB_X[thumb_key])
        self._thumb_animation.start()

    def hitButton(self, position):
        # QCheckBox's default hit area is based on its (empty) text/indicator.
        # The full capsule should respond, including clicks around the thumb.
        return self.rect().contains(position)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = self.rect().adjusted(
            appearance.SWITCH_INSET,
            appearance.SWITCH_INSET,
            -appearance.SWITCH_INSET,
            -appearance.SWITCH_INSET,
        )
        if self.isEnabled():
            track_color = (
                self._on_color
                if self.isChecked()
                else self._off_color.lighter(appearance.SWITCH_HOVER_LIGHTEN) if self._hovered else self._off_color
            )
            border_color = self._on_color if self.isChecked() or self.hasFocus() else self._border_color
            thumb_color = self._thumb_color
        else:
            track_color = self._disabled_color
            border_color = self._disabled_color
            thumb_color = self._disabled_thumb_color
        painter.setPen(QPen(border_color, appearance.SWITCH_BORDER_WIDTH))
        painter.setBrush(track_color)
        painter.drawRoundedRect(track, appearance.SWITCH_TRACK_RADIUS, appearance.SWITCH_TRACK_RADIUS)
        thumb_x = round(self._thumb_position)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(thumb_color)
        thumb_size = appearance.SWITCH_THUMB_SIZE
        thumb_y = (self.height() - thumb_size) // 2
        painter.drawEllipse(thumb_x, thumb_y, thumb_size, thumb_size)
