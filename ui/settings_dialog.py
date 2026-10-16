from PySide6.QtCore import QEasingCurve, QPoint, QRect, Property, QPropertyAnimation, QSize, Qt, Signal, QByteArray, QUrl
from PySide6.QtGui import QDesktopServices, QColor, QFont, QFontDatabase, QLinearGradient, QPainter, QPen
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
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
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import (
    CHIP_WIDTH_MAX_LIMIT,
    CHIP_WIDTH_MIN_LIMIT,
    CLIPBOARD_HISTORY_RETENTION_MAX_DAYS,
    CLIPBOARD_HISTORY_RETENTION_MIN_DAYS,
    MAX_CHIPS_MIN,
    MAX_CHIPS_MAX,
    SHELF_WIDTH_RATIO_MAX,
    SHELF_WIDTH_RATIO_MIN,
)
from animation_config import CHIP_SCROLL_SPEED_MIN, CHIP_SCROLL_SPEED_MAX
import ui_config as appearance


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


class SettingsDialog(QDialog):
    def __init__(
        self,
        *,
        show_on_hover,
        hide_on_paste,
        highlight_shelf_on_drag,
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
        max_chips,
        shelf_width_ratio,
        theme_name,
        available_themes,
        theme_previews,
        accent_color,
        accent_options,
        history_dates,
        selected_history_date,
        history_retention_days,
        theme,
        on_show_on_hover,
        on_hide_on_paste,
        on_highlight_shelf_on_drag,
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
        on_max_chips,
        on_shelf_width_ratio,
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
        ):
            self._add_nav_item(icon_name, page_name)
        self.sidebar.currentRowChanged.connect(self._on_nav_changed)
        self.sidebar.setCurrentRow(0)

        general = self._new_page("General", "Choose how DockPaste behaves on your desktop.")
        general_card = self._card(general)
        self.show_on_hover = self._add_switch(
            general_card, "Show Shelf on Hover", "Reveal the shelf when you move to the top edge of the screen.", show_on_hover, on_show_on_hover
        )
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
            general_card, "Skip Items Over 5 MB", "Keep large clipboard items out of local history.", prevent_oversize_items, on_prevent_oversize_items
        )
        self.oversize_warning = self._add_switch(
            general_card, "Warn When an Item Is Skipped", "Show a notice when an item exceeds the size limit.", show_oversize_warning, on_oversize_warning
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
        self.max_chips = self._spin(max_chips, MAX_CHIPS_MIN, MAX_CHIPS_MAX)
        self.max_chips.valueChanged.connect(on_max_chips)
        self._add_control_row(sizing_card, "Maximum Clips", "Maximum number of visible clips in the shelf.", self.max_chips)
        self.shelf_width_ratio = QDoubleSpinBox()
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
        self.history_date_combo = MacComboBox(self._theme_palette)
        for history_date in history_dates:
            self.history_date_combo.addItem(history_date, history_date)
        selected_index = self.history_date_combo.findData(selected_history_date)
        self.history_date_combo.setCurrentIndex(max(0, selected_index))
        self.history_date_combo.currentIndexChanged.connect(
            lambda index: on_history_date(self.history_date_combo.itemData(index))
        )
        self._add_control_row(history_card, "Browse Copy Date", "Show clips copied on this date.", self.history_date_combo)
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
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        spin.setSuffix(suffix)
        spin.setValue(value)
        return spin

    def set_theme(self, theme):
        # Settings share the active theme's colors while keeping their own layout.
        p = {**self._theme_palette, **(theme or {}).get("settings", {})}
        self._theme_palette = p
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
        for combo in self.findChildren(MacComboBox):
            combo.set_theme_colors(p)
        selected_theme = (theme or {}).get("name")
        for theme_id, button in self._theme_buttons.items():
            button.set_palette(p, self._theme_previews.get(theme_id, {}))
            button.setChecked(theme_id == selected_theme)
        for button in self._accent_buttons.values():
            button.set_palette(p)
        self.setWindowTitle(appearance.WINDOW_TITLE)
        self.setStyleSheet(appearance.settings_stylesheet(p))

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


class MacComboBox(QComboBox):
    """Draw a restrained macOS-style popup button and keep Qt's native popup."""

    def __init__(self, palette, parent=None):
        super().__init__(parent)
        self._theme_palette = dict(palette)
        self.setObjectName("macCombo")
        self.setFont(
            QFont(
                appearance.FONT_FAMILY,
                appearance.FONT["control_size"],
                appearance.FONT["control_weight"],
            )
        )
        self.setMinimumWidth(appearance.DROPDOWN_MIN_SIZE[0])
        self.setMinimumHeight(appearance.DROPDOWN_MIN_SIZE[1])
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setMaxVisibleItems(appearance.DROPDOWN_VISIBLE_ITEMS)
        self.view().setMouseTracking(True)
        self.view().viewport().setMouseTracking(True)
        self.view().setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.view().viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.view().setUniformItemSizes(True)
        self.view().setSpacing(appearance.DROPDOWN_ITEM_SPACING)
        self.view().setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view().setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view().setMaximumHeight(appearance.DROPDOWN_MAX_HEIGHT)
        self.view().setStyleSheet(appearance.dropdown_stylesheet(self._theme_palette))
        self._hovered = False

    def set_theme_colors(self, palette):
        self._theme_palette = {**self._theme_palette, **palette}
        self.view().setStyleSheet(appearance.dropdown_stylesheet(self._theme_palette))
        self.update()

    def paintEvent(self, event):
        p = self._theme_palette
        text_color = QColor(p["text"])
        muted = QColor(p["control_border"])
        focus_border = QColor(p["control_focus_border"])
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(*appearance.DROPDOWN_BORDER_INSET)
        border = focus_border if self.hasFocus() else QColor(p["control_hover_border"]) if self._hovered else muted
        painter.setPen(QPen(border, appearance.DROPDOWN_BORDER_WIDTH))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, appearance.DROPDOWN_RADIUS, appearance.DROPDOWN_RADIUS)
        painter.setPen(text_color)
        text_rect = self.rect().adjusted(
            appearance.DROPDOWN_TEXT_INSET,
            0,
            -appearance.DROPDOWN_ICON_GAP,
            0,
        )
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.currentText())
        cx = self.width() - appearance.DROPDOWN_ARROW_INSET
        cy = self.height() // 2
        half_width = appearance.DROPDOWN_ARROW_HALF_WIDTH
        half_height = appearance.DROPDOWN_ARROW_HALF_HEIGHT
        painter.setPen(QPen(text_color, appearance.DROPDOWN_ARROW_STROKE, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawLine(QPoint(cx - half_width, cy - half_height), QPoint(cx, cy + half_height))
        painter.drawLine(QPoint(cx, cy + half_height), QPoint(cx + half_width, cy - half_height))

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)
