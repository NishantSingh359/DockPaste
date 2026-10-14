from PySide6.QtCore import QEasingCurve, QPoint, Property, QPropertyAnimation, QSize, Qt, Signal, QByteArray
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPen
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QAbstractItemView,
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
import settings_config as appearance


class SettingsNavRow(QWidget):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False
        self._hovered = False
        self._accent = QColor(appearance.PALETTE["accent"])
        self._hover_color = QColor(appearance.PALETTE["surface_hover"])

    def set_active(self, active):
        self._active = bool(active)
        self.update()

    def set_colors(self, accent, hover_color):
        self._accent = accent
        self._hover_color = hover_color
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

    def __init__(self, icon_name, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self._active = False
        self.setFixedSize(appearance.NAV_ICON_SIZE, appearance.NAV_ICON_SIZE)

    def set_active(self, active):
        if self._active != bool(active):
            self._active = bool(active)
            self.update()

    def paintEvent(self, event):
        color = appearance.PALETTE["white"] if self._active else appearance.PALETTE["secondary_text"]
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


class SettingsDialog(QDialog):
    def __init__(
        self,
        *,
        show_on_hover,
        hide_on_paste,
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
        history_dates,
        selected_history_date,
        history_retention_days,
        theme,
        on_show_on_hover,
        on_hide_on_paste,
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
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        QFontDatabase.addApplicationFont(str(appearance.FONT_FILE))
        self.resize(*appearance.WINDOW_SIZE)

        root = QHBoxLayout(self)
        root.setContentsMargins(*appearance.ROOT_MARGINS)
        root.setSpacing(appearance.ROOT_SPACING)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("settingsSidebar")
        self.sidebar.setFixedWidth(appearance.SIDEBAR_WIDTH)
        self.sidebar.setSpacing(appearance.SIDEBAR_SPACING)
        self.sidebar.setFrameShape(QFrame.NoFrame)
        self.sidebar.setFocusPolicy(Qt.NoFocus)
        self.sidebar.setUniformItemSizes(True)
        self.sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.pages = QStackedWidget()
        self.pages.setObjectName("settingsPages")
        self.pages.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        root.addWidget(self.sidebar)
        root.addWidget(self.pages, 1)

        self._nav_rows = []
        self._nav_icons = []
        for icon_name, page_name in (("general", "General"), ("appearance", "Appearance"), ("history", "History")):
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
        appearance_card = self._card(appearance_page)
        self.theme_combo = MacComboBox()
        for theme_id, display_name in available_themes:
            self.theme_combo.addItem(display_name, theme_id)
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(theme_name))
        self.theme_combo.currentIndexChanged.connect(
            lambda index: on_theme(self.theme_combo.itemData(index))
        )
        self._add_control_row(appearance_card, "Color Theme", "Choose the color palette used by DockPaste.", self.theme_combo)
        self.show_clip_indexes = self._add_switch(
            appearance_card, "Show Clip Indexes", "Display the keyboard index on each clip.", show_clip_indexes, on_show_clip_indexes
        )
        self.color_preview = self._add_switch(
            appearance_card, "Show Color Previews", "Show a swatch for copied color values.", color_preview_enabled, on_color_preview
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
        self.history_date_combo = MacComboBox()
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

        row = SettingsNavRow()
        row.setObjectName("settingsNavRow")
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(*appearance.NAV_ROW_MARGINS)
        row_layout.setSpacing(appearance.NAV_ROW_SPACING)
        icon = SettingsNavIcon(icon_name)
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

    @staticmethod
    def _switch(title, description, checked, callback):
        checkbox = MacSwitch()
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
        # Settings keep their own appearance, independent of the shelf theme.
        p = appearance.PALETTE
        for row in self.findChildren(SettingsNavRow):
            row.set_colors(QColor(p["accent"]), QColor(p["surface_hover"]))
        for switch in self.findChildren(MacSwitch):
            switch.set_colors(
                QColor(p["accent"]),
                QColor(p["switch_off"]),
                QColor(p["border"]),
                QColor(p["white"]),
                QColor(p["switch_disabled"]),
            )
        self.setWindowTitle(appearance.WINDOW_TITLE)
        self.setStyleSheet(appearance.settings_stylesheet())

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
        dialog.setStyleSheet(appearance.confirmation_stylesheet())
        dialog.exec()
        if dialog.clickedButton() is clear_button:
            callback()


class MacSwitch(QCheckBox):
    """Compact track-and-thumb switch drawn in the macOS settings style."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(*appearance.SWITCH_SIZE)
        self._on_color = QColor(appearance.PALETTE["accent"])
        self._off_color = QColor(appearance.PALETTE["switch_off"])
        self._border_color = QColor(appearance.PALETTE["border"])
        self._thumb_color = QColor(appearance.PALETTE["white"])
        self._disabled_color = QColor(appearance.PALETTE["switch_disabled"])
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
            thumb_color = QColor(appearance.PALETTE["disabled_thumb"])
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

    def __init__(self, parent=None):
        super().__init__(parent)
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
        self.view().setStyleSheet(appearance.dropdown_stylesheet())
        self._hovered = False

    def paintEvent(self, event):
        text_color = QColor(appearance.PALETTE["text"])
        muted = QColor(appearance.PALETTE["control_border"])
        focus_border = QColor(appearance.PALETTE["control_focus_border"])
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(*appearance.DROPDOWN_BORDER_INSET)
        border = focus_border if self.hasFocus() else QColor(appearance.PALETTE["control_hover_border"]) if self._hovered else muted
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
