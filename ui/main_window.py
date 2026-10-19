from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QApplication,
    QSizePolicy,
    QLabel,
    QMenu,
    QGraphicsDropShadowEffect,
    QSystemTrayIcon,
)

from PySide6.QtCore import (
    Qt,
    QTimer,
    QPoint,
    QPropertyAnimation,
    QParallelAnimationGroup,
    QEasingCurve,
    QSize,
    QObject,
    QRunnable,
    QThreadPool,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QCursor,
    QPainter,
    QPainterPath,
    QRegion,
    QIcon,
    QPixmap,
    QBrush,
    QConicalGradient,
)
from PySide6.QtSvg import QSvgRenderer
import ctypes
import ctypes.wintypes
import sys
from datetime import date
from pathlib import Path
try:
    import winreg
except ImportError:
    winreg = None

from core.clipboard_manager import ClipboardManager
from core.dragdrop_handler import DragDropHandler
from core.favicon_service import shutdown_favicon_service
from core.paste_controller import PasteController
from core.user_settings import UserSettingsStore
from ui.chip_bar import ChipBar
from ui.chip_widget import ChipContextMenu, ChipWidget
from ui.settings_dialog import SettingsDialog
from ui import tray_menu as tray_menu_ui
import ui_config
from ui.notification_popup import OversizedItemPopup
from ui.text_preview_dialog import TextPreviewDialog
from ui.animations import EdgeFadeOpacityEffect, fade, parse_color
from ui.theme_manager import ThemeManager, get_theme_value, set_active_theme
from animation_config import (
    CHIP_CONTEXT_MENU_FADE_OUT_MS,
    CHIP_LAYOUT_ANIMATION_MS,
    MOTION_ENABLED,
    MOTION_SHELF_MS,
    SHELF_CHIP_REVEAL_ENABLED,
    SHELF_CHIP_REVEAL_MS,
    SHELF_CHIP_REVEAL_STAGGER_MS,
    SHELF_CHIP_REVEAL_OFFSET,
    CHIP_SCROLL_SPEED,
    CHIP_SCROLL_SPEED_MIN,
    CHIP_SCROLL_SPEED_MAX,
    DROP_BORDER_ANIMATION_ENABLED,
    DROP_BORDER_COLOR_START,
    DROP_BORDER_COLOR_END,
    DROP_BORDER_ANIMATION_MS,
    DROP_BORDER_ANIMATION_INTERVAL_MS,
    DROP_BORDER_WIDTH,
)
from config import (
    APP_NAME,
    APP_STORAGE_DIR,
    CHIP_WIDTH_DEFAULTS_VERSION,
    CLIPBOARD_HISTORY_RETENTION_DAYS,
    CLIPBOARD_HISTORY_RETENTION_MAX_DAYS,
    CLIPBOARD_HISTORY_RETENTION_MIN_DAYS,
    CHIP_MIN_WIDTH,
    CHIP_MAX_WIDTH,
    CHIP_WIDTH_MIN_LIMIT,
    CHIP_WIDTH_MAX_LIMIT,
    COLOR_PREVIEW_ENABLED,
    HIDE_DISTANCE,
    HOVER_TRIGGER_HEIGHT,
    HOVER_TRIGGER_WIDTH,
    MOUSE_POLL_MS,
    SHELF_SHOW_ON_HOVER,
    HIDE_ON_PASTE,
    clip_indexing,
    SHELF_WIDTH_RATIO,
    SHELF_WIDTH_RATIO_MIN,
    SHELF_WIDTH_RATIO_MAX,
    SHELF_AUTO_HIDE_DELAY
)
from utils.app_logging import log_exception, safe_slot
from utils.app_icon import create_app_icon


class HistoryLoadSignals(QObject):
    completed = Signal(int, str, object, bool, str)


class HistoryLoadTask(QRunnable):
    """Read one date's clip records away from the GUI thread."""

    def __init__(self, database, generation, clip_date, cursor=None, page_size=100):
        super().__init__()
        self.database = database
        self.generation = generation
        self.clip_date = clip_date
        self.cursor = cursor
        self.page_size = page_size
        self.signals = HistoryLoadSignals()

    def run(self):
        try:
            records, has_more = self.database.get_by_date_page(
                self.clip_date, self.page_size, self.cursor
            )
            self.signals.completed.emit(
                self.generation, self.clip_date, records, has_more, ""
            )
        except Exception as exc:
            self.signals.completed.emit(
                self.generation, self.clip_date, None, False, str(exc)
            )


class ShelfContainer(QWidget):
    """Custom container widget with rounded corners."""
    def __init__(self, theme):
        super().__init__()
        self.setObjectName("shelfContainer")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.theme = theme
        self.drop_target_active = False
        self._drop_border_angle = 0.0
        self._drop_border_timer = QTimer(self)
        self._drop_border_timer.setInterval(
            max(16, int(DROP_BORDER_ANIMATION_INTERVAL_MS))
        )
        self._drop_border_timer.timeout.connect(self._advance_drop_border_gradient)
        self._set_theme_values()

    def _set_theme_values(self):
        shelf = self.theme.get("shelf", {})
        self.background_color = shelf.get("background", "rgba(20, 20, 20, 1)")
        self.border_color = shelf.get("border", "rgba(255, 255, 255, 0.07)")
        self.shadow_color = shelf.get("shadow", "rgba(0, 0, 0, 0.4)")
        self.height = int(shelf.get("height", 52))
        self.border_width = float(shelf.get("border_width", 1))
        self.border_radius = float(shelf.get("border_radius", 27))
        self.shadow_blur_radius = float(shelf.get("shadow_blur_radius", 10))
        self.shadow_offset = tuple(shelf.get("shadow_offset", [0, 2]))
        self.setFixedHeight(self.height)
        self._apply_shadow()
        self.update()

    def _apply_shadow(self):
        self.setGraphicsEffect(None)
        if self.shadow_blur_radius > 0:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(self.shadow_blur_radius)
            shadow.setOffset(*self.shadow_offset)
            shadow.setColor(parse_color(self.shadow_color))
            self.setGraphicsEffect(shadow)

    def set_theme(self, theme):
        self.theme = theme
        self._set_theme_values()

    def set_drop_target_active(self, active):
        active = bool(active)
        if self.drop_target_active == active:
            return
        self.drop_target_active = active
        if active and MOTION_ENABLED and DROP_BORDER_ANIMATION_ENABLED:
            self._drop_border_angle = 0.0
            self._drop_border_timer.start()
        else:
            self._drop_border_timer.stop()
        self.update()

    def _advance_drop_border_gradient(self):
        duration = max(1, int(DROP_BORDER_ANIMATION_MS))
        interval = max(16, int(DROP_BORDER_ANIMATION_INTERVAL_MS))
        self._drop_border_angle = (
            self._drop_border_angle + 360.0 * interval / duration
        ) % 360.0
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        path = QPainterPath()
        rect = self.rect()
        border_width = (
            max(self.border_width, float(DROP_BORDER_WIDTH))
            if self.drop_target_active
            else self.border_width
        )
        if border_width > 0:
            margin = border_width / 2.0
            rect_f = rect.toRectF().adjusted(margin, margin, -margin, -margin)
        else:
            rect_f = rect.toRectF()
            
        path.addRoundedRect(rect_f, self.border_radius, self.border_radius)
        
        bg_color = parse_color(self.background_color)
        painter.fillPath(path, bg_color)
        
        if border_width > 0:
            pen = painter.pen()
            pen.setWidthF(border_width)
            if self.drop_target_active:
                if MOTION_ENABLED and DROP_BORDER_ANIMATION_ENABLED:
                    gradient = QConicalGradient(
                        rect_f.center(), self._drop_border_angle
                    )
                    gradient.setColorAt(0.0, parse_color(DROP_BORDER_COLOR_START))
                    gradient.setColorAt(0.5, parse_color(DROP_BORDER_COLOR_END))
                    gradient.setColorAt(1.0, parse_color(DROP_BORDER_COLOR_START))
                    pen.setBrush(QBrush(gradient))
                else:
                    pen.setColor(parse_color(DROP_BORDER_COLOR_START))
            else:
                pen.setColor(parse_color(self.border_color))
            painter.setPen(pen)
            painter.drawPath(path)
        
        painter.end()
        super().paintEvent(event)



class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(APP_NAME)
        self.is_open = False
        self._target_pos = None
        self.last_target_window = None
        self.chips_by_content = {}
        self._clip_dates_by_content = {}
        self._history_load_generation = 0
        self._history_render_generation = 0
        self._history_load_tasks = {}
        self._history_live_additions = {}
        self._history_records_to_render = []
        self._history_pending_records = {}
        self._history_placeholders = {}
        self._history_page_cursor = None
        self._history_has_more = False
        self._history_page_size = max(
            100, int(ui_config.HISTORY_RENDER_PAGE_SIZE)
        )
        self._history_render_index = 0
        self._history_render_limit = 0
        self._history_loading = False
        self._history_bulk_rendering = False
        self._history_load_pool = QThreadPool(self)
        self._history_load_pool.setMaxThreadCount(1)
        self.is_shelf_pinned = False
        self._is_hiding = False
        self._hotkey_was_down = False
        self._screen_geometry_cache_key = None
        self._chip_position_animation_group = None
        self._chip_position_targets = {}
        self.theme_manager = ThemeManager()
        self._settings_store = UserSettingsStore(self._context_menu_settings_path())
        self._persisted_settings = self._settings_store.load()
        self.theme_name = self.theme_manager.get_theme(
            self._persisted_settings["theme"]
        )["name"]
        self.theme = self.theme_manager.get_theme(self.theme_name)
        accent_options = self.theme.get("accent_options", [])
        saved_accent = self._persisted_settings["accent_color"].upper()
        self.accent_color = next(
            (value for value in accent_options if value.upper() == saved_accent),
            accent_options[0] if accent_options else self.theme["settings"]["accent"],
        )
        self.show_on_hover_enabled = SHELF_SHOW_ON_HOVER
        self.hide_on_paste_enabled = HIDE_ON_PASTE
        self.highlight_shelf_on_drag_enabled = True
        self._is_drag_over_shelf = False
        self.clip_scroll_speed = CHIP_SCROLL_SPEED
        self.clip_indexing_enabled = clip_indexing
        self.color_preview_enabled = COLOR_PREVIEW_ENABLED
        self.text_preview_on_double_click_enabled = False
        self.open_images_on_double_click_enabled = True
        self.prevent_oversize_items_enabled = True
        self.show_oversize_warning_enabled = True
        self.close_to_tray_enabled = True
        self.start_with_windows_enabled = False
        self.chip_min_width = CHIP_MIN_WIDTH
        self.chip_max_width = CHIP_MAX_WIDTH
        self.history_retention_days = CLIPBOARD_HISTORY_RETENTION_DAYS
        self._history_date_filter = date.today().isoformat()
        shelf_theme = self.theme.get("shelf", {})
        self.shelf_width_ratio = float(shelf_theme.get("width_ratio", SHELF_WIDTH_RATIO))
        self._next_chip_number = 1
        self._settings_dialog = None
        self._oversized_item_popup = None
        self._text_preview_dialog = None
        self._shadow_margin = max(
            0,
            int(
                float(shelf_theme.get("shadow_blur_radius", 10)) * 2
                + max(abs(value) for value in shelf_theme.get("shadow_offset", [0, 2]))
            ),
        )
        self._load_context_menu_settings()
        self._save_context_menu_settings()

        # Refresh an existing Run entry. Older versions used sys.argv[0] for
        # source launches, which can contain launcher arguments (for example
        # `python.exe -m unittest`) and create a startup command that opens an
        # unrelated path or fails to launch correctly.
        if self.start_with_windows_enabled:
            try:
                self._set_windows_startup(True)
            except Exception as exc:
                log_exception(f"Failed to repair Windows startup entry: {exc}")

        self._create_tray_icon()

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_StyledBackground)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.paste_controller = PasteController()
        self.dragdrop_handler = DragDropHandler(APP_STORAGE_DIR)
        self.clipboard_manager = ClipboardManager(APP_STORAGE_DIR)
        self.dragdrop_handler.set_size_limit_enabled(self.prevent_oversize_items_enabled)
        self.clipboard_manager.set_size_limit_enabled(self.prevent_oversize_items_enabled)
        self._purge_expired_history()
        self.clipboard_manager.text_copied.connect(self.add_clip)
        self.clipboard_manager.image_copied.connect(self.add_clip)
        self.clipboard_manager.path_copied.connect(self.add_clip)
        self.clipboard_manager.oversized_item_rejected.connect(self._show_oversized_item_popup)

        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(MOTION_SHELF_MS)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

        self.setup_ui()
        self.update_screen_geometry()
        self.move(self.hidden_pos)
        self.refresh_chip_indexes()

        self.auto_hide_timer = QTimer(self)
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide_shelf)
        self._auto_hide_waiting_for_reentry = False

        self.hide_reset_timer = QTimer(self)
        self.hide_reset_timer.setSingleShot(True)
        self.hide_reset_timer.timeout.connect(lambda: setattr(self, "_is_hiding", False))

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_mouse_position)
        self.timer.start(MOUSE_POLL_MS)

        self.hotkey_timer = QTimer()
        self.hotkey_timer.timeout.connect(self.check_toggle_hotkey)
        self.hotkey_timer.start(50)

        self.history_retention_timer = QTimer(self)
        self.history_retention_timer.timeout.connect(self._purge_expired_history)
        self.history_retention_timer.start(24 * 60 * 60 * 1000)

        self._apply_theme(self.theme_name)
        QTimer.singleShot(0, lambda: self._request_history_load(self._history_date_filter))

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            self._shadow_margin,
            self._shadow_margin,
            self._shadow_margin,
            self._shadow_margin,
        )
        main_layout.setSpacing(0)

        self.container = ShelfContainer(self.theme)
        # Background is drawn in ShelfContainer.paintEvent(), so keep widget background unset
        self.container.setStyleSheet("")

        shelf_theme = self.theme.get("shelf", {})
        shelf_padding = shelf_theme.get("padding", [9, 0, 9, 0])
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(*shelf_padding)
        container_layout.setSpacing(int(shelf_theme.get("spacing", 5)))

        self.scroll = ChipBar(self.theme)
        self.scroll.set_scroll_speed(self.clip_scroll_speed)
        self.scroll.horizontalScrollBar().valueChanged.connect(
            self._maybe_load_history_page
        )
        self.scroll.horizontalScrollBar().valueChanged.connect(
            self._schedule_history_virtualization
        )
        self.scroll.horizontalScrollBar().rangeChanged.connect(
            lambda *_: self._maybe_load_history_page()
        )
        self.scroll.horizontalScrollBar().rangeChanged.connect(
            lambda *_: self._schedule_history_virtualization()
        )
        self.scroll.setFixedHeight(
            int(shelf_theme.get("height", 52)) - int(shelf_padding[1]) - int(shelf_padding[3])
        )

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        self.chip_layout = QHBoxLayout(scroll_widget)
        self.chip_layout.setContentsMargins(0, 0, 0, 0)
        self.chip_layout.setSpacing(ui_config.SHELF["chip_spacing"])
        self._scroll_content_widget = scroll_widget

        self.scroll.setWidget(scroll_widget)
        container_layout.addWidget(self.scroll)

        main_layout.addWidget(self.container)
        empty_theme = self.theme.get("empty", {})
        self.empty_state_widget = QWidget()
        self.empty_state_widget.setStyleSheet("background: transparent;")
        self.empty_state_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.empty_state_layout = QHBoxLayout(self.empty_state_widget)
        self.empty_state_layout.setContentsMargins(
            int(empty_theme.get("left_padding", 15)),
            0,
            int(empty_theme.get("padding", [5, 12])[1]),
            0,
        )
        self.empty_state_layout.setSpacing(int(empty_theme.get("icon_spacing", 5)))

        # Parent the icon before making it visible. Without a parent, Qt treats
        # this 22x22 QLabel as a top-level window and briefly flashes it at the
        # center of the screen during startup.
        self.empty_state_icon = QLabel(self.empty_state_widget)
        self.empty_state_icon.setAlignment(Qt.AlignCenter)
        icon_size = int(empty_theme.get("icon_size", 22))
        self.empty_state_icon.setFixedSize(icon_size, icon_size)
        self.empty_state_icon.setVisible(bool(empty_theme.get("icon_enabled", True)))
        if empty_theme.get("icon_enabled", True):
            icon_path = Path(empty_theme.get("icon_path", "assets/icons/clear.svg"))
            if not icon_path.is_absolute():
                icon_path = Path(__file__).resolve().parent.parent / icon_path
            renderer = QSvgRenderer(str(icon_path))
            if renderer.isValid():
                icon_pixmap = QPixmap(icon_size, icon_size)
                icon_pixmap.fill(Qt.transparent)
                icon_painter = QPainter(icon_pixmap)
                renderer.render(icon_painter)
                icon_painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
                icon_painter.fillRect(icon_pixmap.rect(), parse_color(empty_theme.get("icon_color", "rgba(100, 100, 100, 1)")))
                icon_painter.end()
                self.empty_state_icon.setPixmap(icon_pixmap)
            else:
                self.empty_state_icon.hide()

        self.empty_state_layout.addWidget(self.empty_state_icon)

        self.empty_label = QLabel(empty_theme.get("text", "Nothing Here"))
        self.empty_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.empty_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.empty_label.setStyleSheet(f"""
            QLabel {{
                color: {empty_theme.get("text_color", "rgba(100, 100, 100, 1)")};
                font-size: {empty_theme.get("font_size", 17)}px;
                font-weight: {empty_theme.get("font_weight", 600)};
                padding: {empty_theme.get("padding", [5, 12])[0]}px 0px;
            }}
        """)
        self.empty_state_layout.addWidget(self.empty_label)
        self.chip_layout.addWidget(self.empty_state_widget)
        self.chip_layout.addStretch()
        self.update_empty_state()

        self.update_mask()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "container"):
            self.update_mask()

    def update_mask(self):
        self.clearMask()

    @safe_slot("Failed to add clipboard chip")
    def add_clip(self, content, clip_date=None, clip_index=None, pinned=False, _bulk=False):
        clip_date = clip_date or date.today().isoformat()
        if (
            self._history_date_filter is not None
            and self._history_date_filter != clip_date
        ):
            return

        if clip_index is None:
            try:
                clip_index = self.clipboard_manager.get_db().get_daily_index(
                    content, clip_date
                )
            except Exception:
                log_exception("Failed to retrieve clipboard index")

        if not _bulk and clip_date == self._history_date_filter and not self._history_loading:
            prior_record = next(
                (
                    record for record in self._history_records_to_render
                    if record["content"] == content
                ),
                None,
            )
            existing_widget = self.chips_by_content.get(content)
            if prior_record is not None:
                pinned = bool(prior_record.get("pinned", 0))
            elif existing_widget is not None:
                pinned = bool(existing_widget.pinned)
            self._upsert_loaded_history_record(content, clip_date, clip_index, pinned)

        if (
            self._history_loading
            and not _bulk
            and clip_date == self._history_date_filter
        ):
            self._history_live_additions[content] = {
                "content": content,
                "date": clip_date,
                "index": clip_index,
                "pinned": int(bool(pinned)),
            }

        if not _bulk and clip_date == self._history_date_filter:
            pending_record = self._history_pending_records.pop(content, None)
            if pending_record is not None:
                # This clip was copied again while waiting for a later page.
                # It is already inserted at its new position below, so skip
                # the stale copy when its old page position is reached.
                pending_record["_skip_render"] = True

        self._clip_dates_by_content[content] = clip_date
        existing_chip = self.chips_by_content.get(content)
        if existing_chip is not None:
            if clip_index is not None:
                existing_chip.set_clip_index(
                    clip_index,
                    show_index=self.clip_indexing_enabled,
                )
                if not _bulk:
                    # Resurfacing a duplicate renumbers every clip for that day.
                    # Refresh all cached indexes before sorting; otherwise the
                    # shelf can compare the new index against stale sibling indexes.
                    self._refresh_clip_indexes_for_date(clip_date)
                    if not self._history_placeholders:
                        self._reorder_chip(existing_chip)
                    self.scroll.horizontalScrollBar().setValue(
                        self.scroll.horizontalScrollBar().minimum()
                    )
            return
        self.add_chip(content, clip_index, pinned=pinned, bulk=_bulk)

    def set_history_date_filter(self, clip_date):
        clip_date = clip_date or date.today().isoformat()
        if clip_date == self._history_date_filter:
            return
        self._request_history_load(clip_date)

    def _request_history_load(self, clip_date):
        clip_date = clip_date or date.today().isoformat()
        self._history_date_filter = clip_date
        self._history_load_generation += 1
        self._history_render_generation += 1
        generation = self._history_load_generation
        self._history_records_to_render = []
        self._history_pending_records = {}
        self._history_page_cursor = None
        self._history_has_more = False
        self._history_render_index = 0
        self._history_bulk_rendering = False
        self._history_live_additions = {}
        self._set_history_loading(True)
        self._clear_history_chip_widgets()
        self._start_history_page_load(generation, clip_date)

    def _start_history_page_load(self, generation, clip_date):
        task = HistoryLoadTask(
            self.clipboard_manager.get_db(),
            generation,
            clip_date,
            self._history_page_cursor,
            self._history_page_size,
        )
        task.signals.completed.connect(self._on_history_records_loaded)
        self._history_load_tasks[generation] = task
        self._history_load_pool.start(task)

    @Slot(int, str, object, bool, str)
    def _on_history_records_loaded(self, generation, clip_date, records, has_more, error):
        self._history_load_tasks.pop(generation, None)
        if generation != self._history_load_generation:
            return
        if error:
            log_exception(f"Failed to load clipboard history for {clip_date}: {error}")
            self._history_bulk_rendering = False
            self._history_live_additions = {}
            self._set_history_loading(False)
            return
        page_cursor = None
        if records:
            last_page_record = records[-1]
            page_cursor = (
                int(last_page_record.get("pinned", 0)),
                int(last_page_record.get("index") or 0),
                int(last_page_record.get("id") or 0),
            )
        if self._history_live_additions:
            previously_loaded = {
                record["content"] for record in self._history_records_to_render
            }
            records_by_content = {
                record["content"]: record
                for record in (*self._history_records_to_render, *records)
            }
            for content, live_record in self._history_live_additions.items():
                if content in records_by_content:
                    records_by_content[content] = {
                        **records_by_content[content],
                        "index": live_record["index"],
                    }
                else:
                    records_by_content[content] = live_record
            combined_records = sorted(
                records_by_content.values(),
                key=lambda record: (
                    not bool(record.get("pinned", 0)),
                    -int(record.get("index") or 0),
                ),
            )
            self._history_records_to_render = [
                records_by_content[content]
                for content in previously_loaded
                if content in records_by_content
            ]
            self._history_records_to_render.sort(
                key=lambda record: (
                    not bool(record.get("pinned", 0)),
                    -int(record.get("index") or 0),
                )
            )
            loaded_contents = previously_loaded
            records = [
                record for record in combined_records
                if record["content"] not in loaded_contents
            ]
        self._history_live_additions = {}
        existing_contents = {
            record["content"] for record in self._history_records_to_render
        }
        page_contents = set()
        unique_page_records = []
        for record in records:
            content = record["content"]
            if content in existing_contents or content in page_contents:
                continue
            page_contents.add(content)
            unique_page_records.append(record)
        records = unique_page_records
        if not self._history_records_to_render:
            self._history_records_to_render = []
            self._history_render_index = 0
        if records:
            self._history_records_to_render.extend(records)
            self._history_pending_records.update(
                {record["content"]: record for record in records}
            )
        if page_cursor is not None:
            self._history_page_cursor = (
                int(page_cursor[0]),
                int(page_cursor[1]),
                int(page_cursor[2]),
            )
        self._history_has_more = has_more
        self._history_records_to_render.sort(
            key=lambda record: (
                not bool(record.get("pinned", 0)),
                -int(record.get("index") or 0),
                -int(record.get("id") or 0),
            )
        )
        if self._history_render_index:
            self._rebuild_history_layout()
        self._history_render_limit = min(
            len(self._history_records_to_render),
            self._history_render_index + ui_config.HISTORY_RENDER_PAGE_SIZE,
        )
        if self._history_render_index < self._history_render_limit:
            self._history_bulk_rendering = True
            QTimer.singleShot(
                0,
                lambda: self._render_history_batch(self._history_render_generation),
            )
        else:
            self._history_bulk_rendering = False
            self._set_history_loading(False)
            self.update_empty_state()

    def _set_history_loading(self, loading):
        self._history_loading = bool(loading)
        self.update_empty_state()
        if self._settings_dialog is not None:
            self._settings_dialog.set_history_loading(self._history_loading)

    def _show_history_records(self, records):
        self._history_render_generation += 1
        generation = self._history_render_generation
        self._clear_history_chip_widgets()
        self._history_records_to_render = list(records)
        self._history_pending_records = {
            record["content"]: record for record in self._history_records_to_render
        }
        self._history_render_index = 0
        self._history_page_cursor = None
        self._history_has_more = False
        self._history_render_limit = min(
            len(self._history_records_to_render),
            ui_config.HISTORY_RENDER_PAGE_SIZE,
        )
        self._history_bulk_rendering = bool(records)
        self.scroll.horizontalScrollBar().setValue(
            self.scroll.horizontalScrollBar().minimum()
        )
        if not records:
            self._history_bulk_rendering = False
            self.update_empty_state()
            self._set_history_loading(False)
            return
        self._set_history_loading(True)
        QTimer.singleShot(0, lambda: self._render_history_batch(generation))

    def _clear_history_chip_widgets(self):
        chips = list(self.chips_by_content.values())
        self.chips_by_content.clear()
        self._clip_dates_by_content.clear()
        self._remove_chip_widgets(chips)
        for placeholder in self._history_placeholders.values():
            self.chip_layout.removeWidget(placeholder)
            placeholder.deleteLater()
        self._history_placeholders.clear()
        self._next_chip_number = 1

    def _render_history_batch(self, generation):
        if generation != self._history_render_generation:
            return
        batch_end = min(
            self._history_render_index + ui_config.HISTORY_RENDER_BATCH_SIZE,
            self._history_render_limit,
        )
        while self._history_render_index < batch_end:
            record = self._history_records_to_render[self._history_render_index]
            self._history_render_index += 1
            content = record["content"]
            self._history_pending_records.pop(content, None)
            if record.get("_skip_render"):
                continue
            latest_copy = self._history_live_additions.pop(content, None)
            if latest_copy is not None:
                record = {**record, "index": latest_copy["index"]}
            self.add_clip(
                content,
                record["date"],
                record["index"],
                pinned=bool(record.get("pinned", 0)),
                _bulk=True,
            )
        if self._history_render_index < self._history_render_limit:
            QTimer.singleShot(
                ui_config.HISTORY_RENDER_INTERVAL_MS,
                lambda: self._render_history_batch(generation),
            )
            return

        self._history_bulk_rendering = False
        self._schedule_history_virtualization()
        self.scroll.refresh_edge_fades()
        self.update_empty_state()
        self._set_history_loading(False)
        if self._history_render_index < len(self._history_records_to_render):
            self._maybe_load_history_page()
        elif not self._history_has_more:
            self._history_pending_records = {}
            self._history_live_additions = {}

    def _maybe_load_history_page(self, *_):
        if (
            self._history_loading
            or self._history_bulk_rendering
        ):
            return

        scrollbar = self.scroll.horizontalScrollBar()
        near_end = (
            scrollbar.maximum() == scrollbar.minimum()
            or scrollbar.maximum() - scrollbar.value()
            <= max(self.scroll.viewport().width(), 1)
        )
        if not near_end:
            return

        if self._history_render_index < len(self._history_records_to_render):
            self._history_render_limit = min(
                len(self._history_records_to_render),
                self._history_render_index + ui_config.HISTORY_RENDER_PAGE_SIZE,
            )
            self._history_bulk_rendering = True
            self._set_history_loading(True)
            generation = self._history_render_generation
            QTimer.singleShot(0, lambda: self._render_history_batch(generation))
        elif self._history_has_more:
            self._history_loading = True
            self._set_history_loading(True)
            self._start_history_page_load(
                self._history_load_generation,
                self._history_date_filter,
            )

    def _schedule_history_virtualization(self):
        if getattr(self, "_history_virtualization_pending", False):
            return
        self._history_virtualization_pending = True
        QTimer.singleShot(0, self._virtualize_history_chips)

    def _virtualize_history_chips(self):
        self._history_virtualization_pending = False
        if not hasattr(self, "_scroll_content_widget"):
            return

        scrollbar = self.scroll.horizontalScrollBar()
        left = max(0, scrollbar.value() - self.scroll.viewport().width())
        right = scrollbar.value() + 2 * self.scroll.viewport().width()
        spacing = self.chip_layout.spacing()
        x = 0
        visible_record_count = min(
            self._history_render_index,
            len(self._history_records_to_render),
        )

        for index in range(visible_record_count):
            record = self._history_records_to_render[index]
            content = record["content"]
            chip = self.chips_by_content.get(content)
            placeholder = self._history_placeholders.get(content)
            item = chip or placeholder
            if item is None:
                continue
            width = item.width() if chip else placeholder.width()
            item_left, item_right = x, x + width
            should_be_materialized = item_right >= left and item_left <= right
            layout_index = index + 1  # The empty-state widget occupies slot zero.

            if should_be_materialized and placeholder is not None:
                self._history_placeholders.pop(content, None)
                self.chip_layout.removeWidget(placeholder)
                placeholder.deleteLater()
                self._clip_dates_by_content[content] = record.get("date")
                self.add_chip(
                    content,
                    record.get("index"),
                    pinned=bool(record.get("pinned", 0)),
                    bulk=True,
                    _layout_index=layout_index,
                )
                chip = self.chips_by_content.get(content)
                if chip is not None:
                    chip.show()
                    width = chip.width()
                    item_right = item_left + width
            elif should_be_materialized and chip is not None:
                chip.show()
            elif not should_be_materialized and chip is not None:
                width = chip.width()
                self.chip_layout.removeWidget(chip)
                placeholder = QWidget(self._scroll_content_widget)
                placeholder.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                placeholder.setFixedSize(width, chip.height())
                self.chip_layout.insertWidget(layout_index, placeholder)
                self._history_placeholders[content] = placeholder
                self.chips_by_content.pop(content, None)
                chip.hide()
                chip.setGraphicsEffect(None)
                chip.deleteLater()

            x = item_right + spacing
        self.scroll.refresh_edge_fades()

    def _rebuild_history_layout(self):
        """Reorder materialized chips and placeholders to match the record model."""
        if not hasattr(self, "_scroll_content_widget"):
            return
        old_scroll = self.scroll.horizontalScrollBar().value()
        retained = {**self.chips_by_content, **self._history_placeholders}
        while self.chip_layout.count():
            item = self.chip_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None and widget is not self.empty_state_widget:
                widget.hide()
        self.chip_layout.addWidget(self.empty_state_widget)

        visible_count = min(self._history_render_index, len(self._history_records_to_render))
        for record in self._history_records_to_render[:visible_count]:
            content = record["content"]
            widget = retained.get(content)
            if widget is None:
                self._clip_dates_by_content[content] = record.get("date")
                self.add_chip(
                    content,
                    record.get("index"),
                    pinned=bool(record.get("pinned", 0)),
                    bulk=True,
                    _layout_index=self.chip_layout.count(),
                )
                widget = self.chips_by_content.get(content)
            elif isinstance(widget, ChipWidget):
                self.chip_layout.addWidget(widget)
                widget.show()
            else:
                self.chip_layout.addWidget(widget)
                widget.show()
        self.chip_layout.addStretch()
        self.scroll.horizontalScrollBar().setValue(old_scroll)
        self._schedule_history_virtualization()

    def _upsert_loaded_history_record(self, content, clip_date, clip_index, pinned):
        if clip_date != self._history_date_filter or self._history_loading:
            return
        record = next(
            (item for item in self._history_records_to_render if item["content"] == content),
            None,
        )
        if record is None:
            record = {"content": content, "date": clip_date, "index": clip_index, "pinned": int(bool(pinned))}
            self._history_records_to_render.append(record)
            self._history_render_index += 1
        else:
            record["index"] = clip_index
            record["pinned"] = int(bool(pinned))
        self._history_records_to_render.sort(
            key=lambda item: (
                not bool(item.get("pinned", 0)),
                -int(item.get("index") or 0),
                -int(item.get("id") or 0),
            )
        )
        self._history_pending_records[content] = record
        self._rebuild_history_layout()

    @safe_slot("Failed to create clipboard chip")
    def add_chip(self, content, clip_index=None, pinned=False, bulk=False, _layout_index=None):
        if content in self.chips_by_content:
            return

        if not bulk:
            self._finish_chip_position_animation()
        chip = ChipWidget(
            content,
            self.chip_min_width,
            self.chip_max_width,
            color_preview_enabled=self.color_preview_enabled,
            text_preview_enabled=self.text_preview_on_double_click_enabled,
            open_images_on_double_click=self.open_images_on_double_click_enabled,
            theme=self.theme,
        )
        chip.pinned = bool(pinned)
        chip.apply_style()
        self._assign_chip_number(chip, clip_index)
        chip.paste_requested.connect(self.paste_clip)
        chip.text_preview_requested.connect(self._show_text_preview)
        chip.image_opening.connect(self.clipboard_manager.ignore_image_capture)
        chip.copy_again_requested.connect(self.copy_again_clip)
        chip.delete_requested.connect(self.remove_clip)
        chip.pin_requested.connect(self.pin_clip)
        chip.clear_all_requested.connect(self.clear_unpinned_clips)
        chip.context_action_triggered.connect(self.keep_shelf_open_after_context_action)
        self.chips_by_content[content] = chip
        self._clip_dates_by_content.setdefault(content, self._history_date_filter)
        if bulk:
            if _layout_index is None:
                _layout_index = max(0, self.chip_layout.count() - 1)
            self.chip_layout.insertWidget(_layout_index, chip)
        else:
            self.update_empty_state()
            self.insert_chip(chip)
            self.refresh_chip_indexes()
        chip.show()
        if not bulk:
            self.scroll.refresh_edge_fades()
            chip._entry_fade_animation = fade(
                chip,
                0.0,
                1.0,
                CHIP_LAYOUT_ANIMATION_MS,
                finished=lambda: self._finish_chip_fade_in(chip),
            )

    def add_clips(self, contents):
        for content in contents:
            self.add_clip(content)

    @safe_slot("Failed to remove clipboard chip")
    def remove_clip(self, content):
        chip = self.chips_by_content.pop(content, None)
        placeholder = self._history_placeholders.pop(content, None)
        if not chip and not placeholder:
            return

        clip_date = self._clip_dates_by_content.pop(content, None)
        try:
            self.clipboard_manager.get_db().delete_by_content(content, clip_date)
        except Exception:
            log_exception("Failed to delete clipboard item")
        if placeholder:
            self.chip_layout.removeWidget(placeholder)
            placeholder.deleteLater()
        if chip:
            self.remove_chip_widget(chip)
        removed_index = next(
            (i for i, record in enumerate(self._history_records_to_render) if record["content"] == content),
            None,
        )
        if removed_index is not None:
            self._history_records_to_render.pop(removed_index)
            self._history_pending_records.pop(content, None)
            if removed_index < self._history_render_index:
                self._history_render_index -= 1
            self._history_render_limit = max(
                self._history_render_index,
                self._history_render_limit - (removed_index < self._history_render_limit),
            )
            self._rebuild_history_layout()
        self._refresh_clip_indexes_for_date(clip_date)

    def remove_chip_widget(self, chip):
        self._remove_chip_widgets([chip])

    def _remove_chip_widgets(self, chips):
        chips = [chip for chip in chips if not getattr(chip, "_is_deleting", False)]
        if not chips:
            return

        self._finish_chip_position_animation()
        start_positions = {chip: chip.pos() for chip in self.chip_widgets()}
        for chip in chips:
            chip._is_deleting = True
            chip.setEnabled(False)
            chip.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            entry_animation = getattr(chip, "_entry_fade_animation", None)
            if entry_animation is not None:
                entry_animation.stop()
                chip._entry_fade_animation = None
            chip.hide()
            chip.setGraphicsEffect(None)
            self.chip_layout.removeWidget(chip)
            chip.deleteLater()

        self.chip_layout.activate()
        self.update_empty_state()
        self.refresh_chip_indexes()
        self._animate_chip_layout(start_positions, CHIP_LAYOUT_ANIMATION_MS)

    @staticmethod
    def _finish_chip_fade_in(chip):
        chip._entry_fade_animation = None
        if not chip._is_deleting:
            effect = chip.graphicsEffect()
            if isinstance(effect, EdgeFadeOpacityEffect):
                effect.base_opacity = 1.0
            else:
                chip.setGraphicsEffect(None)

    def update_empty_state(self):
        if hasattr(self, "empty_label"):
            if self._history_loading:
                self.empty_state_widget.hide()
                return
            has_chip_widgets = False
            for index in range(self.chip_layout.count()):
                item = self.chip_layout.itemAt(index)
                widget = item.widget() if item else None
                if widget and widget is not self.empty_state_widget:
                    has_chip_widgets = True
                    break
            self.empty_state_widget.setVisible(not self.chips_by_content and not has_chip_widgets)

    @safe_slot("Failed to clear unpinned clips")
    def clear_unpinned_clips(self):
        clip_date = self._history_date_filter
        if clip_date is None:
            return
        try:
            self.clipboard_manager.get_db().delete_unpinned(clip_date)
        except Exception:
            log_exception("Failed to delete clipboard items during clear")
            return
        self._request_history_load(clip_date)

    @safe_slot("Failed to pin clipboard chip")
    def pin_clip(self, content):
        chip = self.chips_by_content.get(content)
        if not chip or getattr(chip, "_is_deleting", False):
            return

        clip_date = self._clip_dates_by_content.get(content)
        if clip_date is not None:
            try:
                self.clipboard_manager.get_db().set_pinned(
                    content,
                    clip_date,
                    chip.pinned,
                )
            except Exception:
                log_exception("Failed to save clipboard pin state")
        record = next(
            (item for item in self._history_records_to_render if item["content"] == content),
            None,
        )
        if record is not None:
            record["pinned"] = int(bool(chip.pinned))
            self._history_records_to_render.sort(
                key=lambda item: (
                    not bool(item.get("pinned", 0)),
                    -int(item.get("index") or 0),
                    -int(item.get("id") or 0),
                )
            )
            self._sync_history_page_cursor()
        if self._history_placeholders:
            self._rebuild_history_layout()
        else:
            self._reorder_chip(chip)

    def _reorder_chip(self, chip):
        if not chip or getattr(chip, "_is_deleting", False):
            return
        self._finish_chip_position_animation()
        chip._is_reordering = True
        start_positions = {item: item.pos() for item in self.chip_widgets()}
        self.chip_layout.removeWidget(chip)
        self.insert_chip(chip)
        self.refresh_chip_indexes()
        self._animate_chip_layout(
            start_positions,
            CHIP_LAYOUT_ANIMATION_MS,
            finished=lambda: setattr(chip, "_is_reordering", False),
        )

    def _finish_chip_position_animation(self):
        animation_group = self._chip_position_animation_group
        if animation_group is not None:
            animation_group.stop()
            self._chip_position_animation_group = None
        for chip, target in self._chip_position_targets.items():
            chip.move(target)
        self._chip_position_targets = {}
        self.chip_layout.setEnabled(True)
        self.chip_layout.activate()
        self._clear_chip_reordering_flags()

    def _clear_chip_reordering_flags(self):
        for chip in self.chip_widgets():
            chip._is_reordering = False

    def _animate_chip_layout(self, start_positions, duration, finished=None):
        self.chip_layout.activate()
        target_positions = {
            chip: chip.pos()
            for chip in self.chip_widgets()
            if chip in start_positions
        }
        moving_chips = [
            chip
            for chip, target in target_positions.items()
            if start_positions[chip] != target
        ]

        if not MOTION_ENABLED or duration <= 0 or not moving_chips:
            self.chip_layout.setEnabled(True)
            self.chip_layout.activate()
            self._clear_chip_reordering_flags()
            if finished:
                finished()
            return

        animation_group = QParallelAnimationGroup(self)
        self.chip_layout.setEnabled(False)
        for chip in moving_chips:
            chip.move(start_positions[chip])
            position_animation = QPropertyAnimation(chip, b"pos", animation_group)
            position_animation.setDuration(duration)
            position_animation.setStartValue(start_positions[chip])
            position_animation.setEndValue(target_positions[chip])
            position_animation.setEasingCurve(QEasingCurve.OutCubic)
            animation_group.addAnimation(position_animation)

        def finish_transition():
            self.chip_layout.setEnabled(True)
            self.chip_layout.activate()
            self._chip_position_animation_group = None
            self._chip_position_targets = {}
            self._clear_chip_reordering_flags()
            if finished:
                finished()

        animation_group.finished.connect(finish_transition)
        self._chip_position_animation_group = animation_group
        self._chip_position_targets = target_positions
        self.chip_layout.setEnabled(False)
        animation_group.start()

    def chip_widgets(self):
        chips = []
        for index in range(self.chip_layout.count()):
            item = self.chip_layout.itemAt(index)
            widget = item.widget() if item else None
            if isinstance(widget, ChipWidget):
                chips.append(widget)
        return chips

    def insert_chip(self, chip):
        insert_at = 0
        for layout_index in range(self.chip_layout.count()):
            item = self.chip_layout.itemAt(layout_index)
            if not item:
                continue
            widget = item.widget()
            if widget is None:
                break
            if widget is getattr(self, "empty_state_widget", None):
                continue

            widget_is_pinned = bool(getattr(widget, "pinned", False))
            if widget_is_pinned and not chip.pinned:
                insert_at = layout_index + 1
                continue
            if chip.pinned and not widget_is_pinned:
                break

            existing_number = getattr(widget, "clip_index", None)
            if (
                existing_number is None
                or chip.clip_index is None
                or chip.clip_index > existing_number
            ):
                insert_at = layout_index
                break
            insert_at = layout_index + 1

        self.chip_layout.insertWidget(insert_at, chip)

    def _assign_chip_number(self, chip, clip_index=None):
        if clip_index is None:
            clip_index = self._next_chip_number
        chip.set_clip_index(clip_index, show_index=self.clip_indexing_enabled)
        self._next_chip_number = max(self._next_chip_number, int(clip_index) + 1)

    def _sync_history_page_cursor(self):
        """Keep the keyset cursor aligned when loaded rows are reordered."""
        if self._history_page_cursor is None:
            return
        _, _, cursor_id = self._history_page_cursor
        cursor_record = next(
            (
                record for record in self._history_records_to_render
                if int(record.get("id") or 0) == cursor_id
            ),
            None,
        )
        if cursor_record is not None:
            self._history_page_cursor = (
                int(cursor_record.get("pinned", 0)),
                int(cursor_record.get("index") or 0),
                cursor_id,
            )

    def _refresh_clip_indexes_for_date(self, clip_date):
        if clip_date is None:
            return
        contents = [
            record["content"]
            for record in self._history_records_to_render
            if record.get("date") == clip_date
        ]
        try:
            indexes = self.clipboard_manager.get_db().get_indexes_for_contents(
                clip_date, contents
            )
        except Exception:
            log_exception("Failed to refresh clipboard indexes")
            return
        for record in self._history_records_to_render:
            if record.get("date") == clip_date and record["content"] in indexes:
                record["index"] = indexes[record["content"]]
        self._sync_history_page_cursor()
        self._history_records_to_render.sort(
            key=lambda record: (
                not bool(record.get("pinned", 0)),
                -int(record.get("index") or 0),
                -int(record.get("id") or 0),
            )
        )
        for content, chip in self.chips_by_content.items():
            if self._clip_dates_by_content.get(content) != clip_date:
                continue
            if content in indexes:
                chip.set_clip_index(
                    indexes[content], show_index=self.clip_indexing_enabled
                )
        if self._history_placeholders:
            self._rebuild_history_layout()

    def refresh_chip_indexes(self):
        chips = []
        for layout_index in range(self.chip_layout.count()):
            item = self.chip_layout.itemAt(layout_index)
            widget = item.widget() if item else None
            if widget is None or widget is getattr(self, "empty_state_widget", None):
                continue
            if hasattr(widget, "set_clip_index"):
                chips.append(widget)

        for chip in chips:
            if chip.clip_index is None:
                self._assign_chip_number(chip)
            else:
                chip.set_clip_index(chip.clip_index, show_index=self.clip_indexing_enabled)

    @safe_slot("Failed to paste clipboard chip")
    def paste_clip(self, content):
        chip = self.chips_by_content.get(content)
        if chip and chip.kind == "IMG":
            clipboard_ready = self.clipboard_manager.set_image_for_paste(content, temporary=True)
        else:
            clipboard_ready = self.clipboard_manager.set_text_for_paste(content, temporary=True)
        if not clipboard_ready:
            return

        if self.hide_on_paste_enabled:
            self.hide_shelf()

        QTimer.singleShot(
            MOTION_SHELF_MS,
            lambda: self.paste_controller.paste_text(content, self.last_target_window)
        )
        QTimer.singleShot(
            MOTION_SHELF_MS + 220,
            self.clipboard_manager.restore_previous_clipboard
        )

    @safe_slot("Failed to copy chip content again")
    def copy_again_clip(self, content):
        chip = self.chips_by_content.get(content)
        if chip and chip.kind == "IMG":
            self.clipboard_manager.set_image_for_paste(content, temporary=False)
        else:
            self.clipboard_manager.set_text_for_paste(content, temporary=False)

    @safe_slot("Failed to process drag enter")
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-copypin-chip"):
            self._set_drop_target_hovered(False)
            event.ignore()
            return
        if self.dragdrop_handler.can_accept(event.mimeData()):
            self._set_drop_target_hovered(True)
            event.acceptProposedAction()
        else:
            self._set_drop_target_hovered(False)
            event.ignore()

    @safe_slot("Failed to process drag move")
    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-copypin-chip"):
            self._set_drop_target_hovered(False)
            event.ignore()
            return
        if self.dragdrop_handler.can_accept(event.mimeData()):
            self._set_drop_target_hovered(True)
            event.acceptProposedAction()
        else:
            self._set_drop_target_hovered(False)
            event.ignore()

    def dragLeaveEvent(self, event):
        self._set_drop_target_hovered(False)
        super().dragLeaveEvent(event)

    @safe_slot("Failed to process drop")
    def dropEvent(self, event):
        self._set_drop_target_hovered(False)
        if event.mimeData().hasFormat("application/x-copypin-chip"):
            event.ignore()
            return
        items = self.dragdrop_handler.extract_items(event.mimeData())
        if getattr(self.dragdrop_handler, "oversized_item_rejected", False) is True:
            self._show_oversized_item_popup()
        if not items:
            event.ignore()
            return

        self.add_clips(items)
        self._set_clipboard_for_drop(items)
        event.acceptProposedAction()

    def _set_clipboard_for_drop(self, items):
        if not items:
            return

        content = items[-1]

        if Path(content).exists() and self.clipboard_manager.set_image_for_paste(content):
            return

        self.clipboard_manager.set_text_for_paste(content)

    # -------------------------
    # HOVER DETECTION
    # -------------------------

    def _set_drop_target_hovered(self, hovered):
        self._is_drag_over_shelf = bool(hovered)
        if hasattr(self, "container"):
            self.container.set_drop_target_active(
                self._is_drag_over_shelf and self.highlight_shelf_on_drag_enabled
            )

    def set_highlight_shelf_on_drag_enabled(self, enabled):
        self.highlight_shelf_on_drag_enabled = bool(enabled)
        self._set_drop_target_hovered(self._is_drag_over_shelf)
        self._save_context_menu_settings()

    def set_clip_scroll_speed(self, speed):
        self.clip_scroll_speed = max(
            CHIP_SCROLL_SPEED_MIN,
            min(CHIP_SCROLL_SPEED_MAX, int(speed)),
        )
        if hasattr(self, "scroll"):
            self.scroll.set_scroll_speed(self.clip_scroll_speed)
        self._save_context_menu_settings()

    def set_show_on_hover_enabled(self, enabled):
        self.show_on_hover_enabled = bool(enabled)
        self._save_context_menu_settings()

    def set_hide_on_paste_enabled(self, enabled):
        self.hide_on_paste_enabled = bool(enabled)
        self._save_context_menu_settings()

    def set_clip_indexing_enabled(self, enabled):
        self.clip_indexing_enabled = bool(enabled)
        self.refresh_chip_indexes()
        self._save_context_menu_settings()

    def set_color_preview_enabled(self, enabled):
        self.color_preview_enabled = bool(enabled)
        for chip in self.chips_by_content.values():
            chip.set_color_preview_enabled(self.color_preview_enabled)
        self._save_context_menu_settings()

    def set_text_preview_on_double_click_enabled(self, enabled):
        self.text_preview_on_double_click_enabled = bool(enabled)
        for chip in self.chips_by_content.values():
            chip.set_text_preview_enabled(self.text_preview_on_double_click_enabled)
        self._save_context_menu_settings()

    def set_open_images_on_double_click_enabled(self, enabled):
        self.open_images_on_double_click_enabled = bool(enabled)
        for chip in self.chips_by_content.values():
            chip.set_open_images_on_double_click(self.open_images_on_double_click_enabled)
        self._save_context_menu_settings()

    @Slot(str)
    def _show_text_preview(self, text):
        screen = QApplication.primaryScreen()
        available_geometry = screen.availableGeometry() if screen is not None else None
        if self._text_preview_dialog is not None:
            try:
                self._text_preview_dialog.close()
            except RuntimeError:
                self._text_preview_dialog = None
        self._text_preview_dialog = TextPreviewDialog(
            text, self.theme, available_geometry
        )
        preview_dialog = self._text_preview_dialog
        self._text_preview_dialog.destroyed.connect(
            lambda _object=None: self._clear_text_preview_reference(preview_dialog)
        )
        self._text_preview_dialog.show()

    def _clear_text_preview_reference(self, preview_dialog):
        if self._text_preview_dialog is preview_dialog:
            self._text_preview_dialog = None

    def set_oversize_warning_enabled(self, enabled):
        self.show_oversize_warning_enabled = bool(enabled) and self.prevent_oversize_items_enabled
        self._save_context_menu_settings()

    def set_oversize_prevention_enabled(self, enabled):
        self.prevent_oversize_items_enabled = bool(enabled)
        self.dragdrop_handler.set_size_limit_enabled(self.prevent_oversize_items_enabled)
        self.clipboard_manager.set_size_limit_enabled(self.prevent_oversize_items_enabled)
        if not self.prevent_oversize_items_enabled:
            self.show_oversize_warning_enabled = False
        self._save_context_menu_settings()

    @Slot()
    def _show_oversized_item_popup(self):
        if not self.prevent_oversize_items_enabled or not self.show_oversize_warning_enabled:
            return
        if self._oversized_item_popup is None:
            self._oversized_item_popup = OversizedItemPopup()
        self._oversized_item_popup.show_notice(self.theme)

    def _context_menu_settings_path(self):
        settings_path = APP_STORAGE_DIR / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        return settings_path

    def _apply_theme(self, theme_name):
        self.theme_name = self.theme_manager.get_theme(theme_name)["name"]
        self.theme = self.theme_manager.with_accent_color(
            self.theme_manager.get_theme(self.theme_name), self.accent_color
        )
        set_active_theme(self.theme_name)
        # Refresh an open Settings window immediately so it cannot retain the
        # previous palette while the shelf and its individual clips update.
        if self._settings_dialog is not None:
            try:
                self._settings_dialog.set_theme(self.theme)
            except RuntimeError:
                self._settings_dialog = None
        if hasattr(self, "scroll"):
            self.scroll.set_theme(self.theme)
        if hasattr(self, "container"):
            self.container.set_theme(self.theme)
        for chip in self.chips_by_content.values():
            chip.set_theme(self.theme)
        if hasattr(self, "empty_label"):
            self._apply_empty_theme()
        if self._text_preview_dialog is not None:
            try:
                self._text_preview_dialog.set_theme(self.theme)
            except RuntimeError:
                self._text_preview_dialog = None
        if self._oversized_item_popup is not None and self._oversized_item_popup.isVisible():
            self._oversized_item_popup.set_theme(self.theme)
        if hasattr(self, "tray_icon") and hasattr(self, "_tray_menu_actions"):
            tray_menu_ui.style_menu(
                self.tray_icon.contextMenu(),
                self._tray_menu_actions,
                self.theme.get("tray_menu", {}),
            )

    def _apply_empty_theme(self):
        empty_theme = self.theme.get("empty", {})
        self.empty_label.setText(empty_theme.get("text", "Nothing Here"))
        self.empty_label.setStyleSheet(f"""
            QLabel {{
                color: {empty_theme.get("text_color", "rgba(100, 100, 100, 1)")};
                font-size: {empty_theme.get("font_size", 17)}px;
                font-weight: {empty_theme.get("font_weight", 600)};
                padding: {empty_theme.get("padding", [5, 12])[0]}px 0px;
            }}
        """)
        if empty_theme.get("icon_enabled", True) and self.empty_state_icon.isVisible():
            icon_path = Path(empty_theme.get("icon_path", "assets/icons/clear.svg"))
            if not icon_path.is_absolute():
                icon_path = Path(__file__).resolve().parent.parent / icon_path
            renderer = QSvgRenderer(str(icon_path))
            if renderer.isValid():
                icon_size = int(empty_theme.get("icon_size", 22))
                pixmap = QPixmap(icon_size, icon_size)
                pixmap.fill(Qt.transparent)
                painter = QPainter(pixmap)
                renderer.render(painter)
                painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
                painter.fillRect(pixmap.rect(), parse_color(empty_theme.get("icon_color", "rgba(100, 100, 100, 1)")))
                painter.end()
                self.empty_state_icon.setPixmap(pixmap)

    def set_theme(self, theme_name):
        theme_name = self.theme_manager.get_theme(theme_name)["name"]
        if theme_name == self.theme_name:
            return
        self.theme_name = theme_name
        self.theme = self.theme_manager.get_theme(theme_name)
        accent_options = self.theme.get("accent_options", [])
        if self.accent_color.upper() not in {value.upper() for value in accent_options}:
            self.accent_color = (
                accent_options[0]
                if accent_options
                else self.theme["settings"]["accent"]
            )
        self._apply_theme(theme_name)
        self._save_context_menu_settings()

    def set_accent_color(self, color):
        color = str(color).upper()
        available = {
            value.upper()
            for value in self.theme_manager.get_theme(self.theme_name).get("accent_options", [])
        }
        if color not in available or color == self.accent_color.upper():
            return
        self.accent_color = color
        self._apply_theme(self.theme_name)
        self._save_context_menu_settings()

    def _load_context_menu_settings(self):
        try:
            settings = self._persisted_settings
            needs_sizing_defaults_migration = (
                settings.get("chip_width_defaults_version", 0) < CHIP_WIDTH_DEFAULTS_VERSION
            )
            self.show_on_hover_enabled = settings["show_on_hover_enabled"]
            self.hide_on_paste_enabled = settings["hide_on_paste_enabled"]
            self.highlight_shelf_on_drag_enabled = settings["highlight_shelf_on_drag_enabled"]
            self.clip_scroll_speed = settings["clip_scroll_speed"]
            self.clip_indexing_enabled = settings["clip_indexing_enabled"]
            self.color_preview_enabled = settings["color_preview_enabled"]
            self.text_preview_on_double_click_enabled = settings["text_preview_on_double_click_enabled"]
            self.open_images_on_double_click_enabled = settings["open_images_on_double_click_enabled"]
            self.prevent_oversize_items_enabled = settings["prevent_oversize_items_enabled"]
            self.show_oversize_warning_enabled = settings["show_oversize_warning_enabled"]
            self.close_to_tray_enabled = settings["close_to_tray_enabled"]
            self.start_with_windows_enabled = settings["start_with_windows_enabled"]
            self.theme_name = self.theme_manager.get_theme(settings.get("theme", self.theme_name))["name"]
            self.theme = self.theme_manager.get_theme(self.theme_name)
            accent_options = self.theme.get("accent_options", [])
            saved_accent = settings["accent_color"].upper()
            self.accent_color = (
                saved_accent if saved_accent in {value.upper() for value in accent_options}
                else (accent_options[0] if accent_options else self.theme["settings"]["accent"])
            )
            self.history_retention_days = settings["history_retention_days"]
            if needs_sizing_defaults_migration:
                self.chip_min_width = CHIP_MIN_WIDTH
                self.chip_max_width = CHIP_MAX_WIDTH
                self.shelf_width_ratio = SHELF_WIDTH_RATIO
            else:
                self.chip_min_width = settings["chip_min_width"]
                self.chip_max_width = settings["chip_max_width"]
                self.shelf_width_ratio = settings["shelf_width_ratio"]
            if needs_sizing_defaults_migration:
                self._save_context_menu_settings()
        except Exception as exc:
            log_exception(f"Failed to load context menu settings: {exc}")

    def _save_context_menu_settings(self):
        self._persisted_settings = self._settings_store.save(
            {
                "show_on_hover_enabled": self.show_on_hover_enabled,
                "hide_on_paste_enabled": self.hide_on_paste_enabled,
                "highlight_shelf_on_drag_enabled": self.highlight_shelf_on_drag_enabled,
                "clip_scroll_speed": self.clip_scroll_speed,
                "clip_indexing_enabled": self.clip_indexing_enabled,
                "color_preview_enabled": self.color_preview_enabled,
                "text_preview_on_double_click_enabled": self.text_preview_on_double_click_enabled,
                "open_images_on_double_click_enabled": self.open_images_on_double_click_enabled,
                "prevent_oversize_items_enabled": self.prevent_oversize_items_enabled,
                "show_oversize_warning_enabled": self.show_oversize_warning_enabled,
                "close_to_tray_enabled": self.close_to_tray_enabled,
                "start_with_windows_enabled": self.start_with_windows_enabled,
                "chip_min_width": self.chip_min_width,
                "chip_max_width": self.chip_max_width,
                "history_retention_days": self.history_retention_days,
                "shelf_width_ratio": self.shelf_width_ratio,
                "theme": self.theme_name,
                "accent_color": self.accent_color,
                "chip_width_defaults_version": CHIP_WIDTH_DEFAULTS_VERSION,
            }
        )

    def _create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(create_app_icon(), self)
        self.tray_icon.setToolTip(APP_NAME)

        tray_menu = QMenu(self)
        settings_action = tray_menu.addAction("Settings")
        settings_action.triggered.connect(self.open_settings)
        tray_menu.addSeparator()
        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(self.exit_application)
        self._tray_menu_actions = {
            settings_action: "settings",
            exit_action: "exit",
        }
        tray_menu_ui.style_menu(
            tray_menu,
            self._tray_menu_actions,
            self.theme.get("tray_menu", {}),
        )
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def exit_application(self, checked=False):
        # Closing normally hides the shelf when close-to-tray is enabled.
        # Tray Exit must bypass that behavior and run the regular shutdown path.
        self.close_to_tray_enabled = False
        self.tray_icon.hide()
        self.close()

    def open_settings(self):
        if self._settings_dialog is not None and self._settings_dialog.isVisible():
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return

        self._settings_dialog = SettingsDialog(
            show_on_hover=self.show_on_hover_enabled,
            hide_on_paste=self.hide_on_paste_enabled,
            highlight_shelf_on_drag=self.highlight_shelf_on_drag_enabled,
            clip_scroll_speed=self.clip_scroll_speed,
            show_clip_indexes=self.clip_indexing_enabled,
            color_preview_enabled=self.color_preview_enabled,
            text_preview_on_double_click=self.text_preview_on_double_click_enabled,
            open_images_on_double_click=self.open_images_on_double_click_enabled,
            prevent_oversize_items=self.prevent_oversize_items_enabled,
            show_oversize_warning=self.show_oversize_warning_enabled,
            close_to_tray=self.close_to_tray_enabled,
            start_with_windows=self.start_with_windows_enabled,
            chip_min_width=self.chip_min_width,
            chip_max_width=self.chip_max_width,
            shelf_width_ratio=self.shelf_width_ratio,
            history_dates=sorted(
                set(self.clipboard_manager.get_db().get_available_dates())
                | {date.today().isoformat()},
                reverse=True,
            ),
            selected_history_date=self._history_date_filter,
            history_retention_days=self.history_retention_days,
            history_loading=self._history_loading,
            theme_name=self.theme_name,
            available_themes=self.theme_manager.available_themes(),
            theme_previews={
                theme_id: {
                    key: self.theme_manager.get_theme(theme_id)["settings"][key]
                    for key in ("background", "surface", "border", "text", "secondary_text")
                }
                for theme_id, _ in self.theme_manager.available_themes()
            },
            accent_color=self.accent_color,
            accent_options=self.theme.get("accent_options", []),
            theme=self.theme,
            on_show_on_hover=self.set_show_on_hover_enabled,
            on_hide_on_paste=self.set_hide_on_paste_enabled,
            on_highlight_shelf_on_drag=self.set_highlight_shelf_on_drag_enabled,
            on_clip_scroll_speed=self.set_clip_scroll_speed,
            on_show_clip_indexes=self.set_clip_indexing_enabled,
            on_color_preview=self.set_color_preview_enabled,
            on_text_preview_on_double_click=self.set_text_preview_on_double_click_enabled,
            on_open_images_on_double_click=self.set_open_images_on_double_click_enabled,
            on_prevent_oversize_items=self.set_oversize_prevention_enabled,
            on_oversize_warning=self.set_oversize_warning_enabled,
            on_close_to_tray=self.set_close_to_tray_enabled,
            on_start_with_windows=self.set_start_with_windows_enabled,
            on_chip_min_width=self.set_chip_min_width,
            on_chip_max_width=self.set_chip_max_width,
            on_shelf_width_ratio=self.set_shelf_width_ratio,
            on_history_date=self.set_history_date_filter,
            on_history_retention_days=self.set_history_retention_days,
            on_clear_all_history=self.clear_all_history,
            on_theme=self.set_theme,
            on_accent_color=self.set_accent_color,
            parent=None,
        )
        self._settings_dialog.setWindowIcon(create_app_icon())
        self._settings_dialog.show()

    @safe_slot("Failed to clear clipboard history")
    def clear_all_history(self):
        database = self.clipboard_manager.get_db()
        database.clear()
        self.clipboard_manager.image_store.clear_thumbnails()

        self._history_load_generation += 1
        self._history_render_generation += 1
        self._history_records_to_render = []
        self._history_bulk_rendering = False
        self._history_date_filter = date.today().isoformat()
        self._set_history_loading(False)
        self._show_history_records([])
        if hasattr(self, "empty_state_widget"):
            self.empty_state_widget.setVisible(True)

        if self._settings_dialog is not None:
            combo = self._settings_dialog.history_date_combo
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(self._history_date_filter, self._history_date_filter)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

    def set_history_retention_days(self, days):
        self.history_retention_days = max(
            CLIPBOARD_HISTORY_RETENTION_MIN_DAYS,
            min(CLIPBOARD_HISTORY_RETENTION_MAX_DAYS, int(days)),
        )
        self._purge_expired_history()
        if self._history_date_filter is not None:
            self.set_history_date_filter(self._history_date_filter)
        self._save_context_menu_settings()

    @safe_slot("Failed to purge expired clipboard history")
    def _purge_expired_history(self):
        database = self.clipboard_manager.get_db()
        database.purge_old_records(self.history_retention_days)
        self.clipboard_manager.image_store.purge_old_thumbnails(
            self.history_retention_days
        )

    def set_chip_min_width(self, width):
        minimum = CHIP_WIDTH_MIN_LIMIT
        maximum = CHIP_WIDTH_MAX_LIMIT
        self.chip_min_width = max(minimum, min(maximum, int(width)))
        if self.chip_min_width > self.chip_max_width:
            self.chip_max_width = self.chip_min_width
            if self._settings_dialog is not None:
                self._settings_dialog.chip_max_width.blockSignals(True)
                self._settings_dialog.chip_max_width.setValue(self.chip_max_width)
                self._settings_dialog.chip_max_width.blockSignals(False)
        self._apply_chip_width_settings()

    def set_chip_max_width(self, width):
        minimum = CHIP_WIDTH_MIN_LIMIT
        maximum = CHIP_WIDTH_MAX_LIMIT
        self.chip_max_width = max(minimum, min(maximum, int(width)))
        if self.chip_max_width < self.chip_min_width:
            self.chip_min_width = self.chip_max_width
            if self._settings_dialog is not None:
                self._settings_dialog.chip_min_width.blockSignals(True)
                self._settings_dialog.chip_min_width.setValue(self.chip_min_width)
                self._settings_dialog.chip_min_width.blockSignals(False)
        self._apply_chip_width_settings()

    def _apply_chip_width_settings(self):
        for chip in self.chips_by_content.values():
            chip.min_width = self.chip_min_width
            chip.max_width = self.chip_max_width
            chip.update_label()
        self._save_context_menu_settings()

    def set_shelf_width_ratio(self, ratio):
        self.shelf_width_ratio = max(
            SHELF_WIDTH_RATIO_MIN,
            min(SHELF_WIDTH_RATIO_MAX, float(ratio)),
        )
        self._screen_geometry_cache_key = None
        self.update_screen_geometry()
        if self.is_open:
            self.animate_to(self.open_pos)
        else:
            self.move(self.hidden_pos)
        self._save_context_menu_settings()

    def set_close_to_tray_enabled(self, enabled):
        self.close_to_tray_enabled = bool(enabled)
        self._save_context_menu_settings()

    def set_start_with_windows_enabled(self, enabled):
        enabled = bool(enabled)
        try:
            self._set_windows_startup(enabled)
        except Exception as exc:
            log_exception(f"Failed to update Windows startup setting: {exc}")
            if self._settings_dialog is not None:
                self._settings_dialog.start_with_windows.setChecked(not enabled)
            return
        self.start_with_windows_enabled = enabled
        self._save_context_menu_settings()

    @staticmethod
    def _set_windows_startup(enabled):
        if sys.platform != "win32" or winreg is None:
            return

        run_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, run_key_path) as run_key:
            if enabled:
                if getattr(sys, "frozen", False):
                    command = f'"{sys.executable}"'
                else:
                    script_path = Path(__file__).resolve().parents[1] / "main.py"
                    command = f'"{sys.executable}" "{script_path}"'
                winreg.SetValueEx(run_key, "DockPaste", 0, winreg.REG_SZ, command)
            for value_name in ("ClipFlow", "DockPaste"):
                if enabled and value_name == "DockPaste":
                    continue
                try:
                    winreg.DeleteValue(run_key, value_name)
                except FileNotFoundError:
                    pass

    def closeEvent(self, event):
        if self.close_to_tray_enabled:
            event.ignore()
            self.hide_shelf(force=True)
            return
        self.tray_icon.hide()
        event.accept()
        QApplication.quit()

    def _cursor_over_chip_context_menu(self, cursor):
        popup = self._active_chip_context_menu()
        if popup is None or not popup.frameGeometry().contains(cursor):
            return False

        return True

    def _active_chip_context_menu(self):
        popup = QApplication.activePopupWidget()
        if not isinstance(popup, ChipContextMenu):
            return None
        parent = popup.parentWidget()
        while parent is not None and parent is not self:
            parent = parent.parentWidget()
        return popup if parent is self else None

    @safe_slot("Failed to check mouse position")
    def check_mouse_position(self):
        is_dragging = False
        if sys.platform == "win32":
            is_dragging = bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)
        else:
            is_dragging = bool(QApplication.mouseButtons() & Qt.LeftButton)

        cursor = QCursor.pos()

        if self.is_shelf_pinned or self._is_hiding:
            return

        if self._cursor_over_chip_context_menu(cursor):
            if self.auto_hide_timer.isActive():
                self.auto_hide_timer.stop()
            return
            
        if not self.show_on_hover_enabled and not is_dragging and not self.is_open:
            return

        self.update_screen_geometry("cursor")
        mouse_y = cursor.y()

        if self.is_open:
            # Use the same hide margin on both the top and bottom edges so
            # Windows dock/taskbar gaps do not leave the shelf partially visible.
            active_area = self.geometry().adjusted(
                -8,
                -HIDE_DISTANCE,
                8,
                HIDE_DISTANCE,
            )
            if self._auto_hide_waiting_for_reentry:
                if active_area.contains(cursor):
                    self._auto_hide_waiting_for_reentry = False
                else:
                    if self.auto_hide_timer.isActive():
                        self.auto_hide_timer.stop()
                    return

            if not active_area.contains(cursor):
                if not self.auto_hide_timer.isActive():
                    self.auto_hide_timer.start(SHELF_AUTO_HIDE_DELAY)
            else:
                if self.auto_hide_timer.isActive():
                    self.auto_hide_timer.stop()
            return

        edge_geometry = getattr(self, "full_screen_geometry", self.screen_geometry)
        hover_threshold = edge_geometry.top() + max(HOVER_TRIGGER_HEIGHT, 1)
        is_over_top_edge = (
            self.trigger_left <= cursor.x() <= self.trigger_right
            and mouse_y <= hover_threshold
        )
        if is_over_top_edge:
            self.show_shelf("cursor")

    def keep_shelf_open_after_context_action(self):
        self._auto_hide_waiting_for_reentry = True
        if self.auto_hide_timer.isActive():
            self.auto_hide_timer.stop()

    def show_shelf(self, monitor_hint="cursor"):
        self.update_screen_geometry(monitor_hint)
        self.last_target_window = self.paste_controller.foreground_window()
        self._is_hiding = False
        self._auto_hide_waiting_for_reentry = False
        if self.hide_reset_timer.isActive():
            self.hide_reset_timer.stop()

        self.is_open = True

        # Make sure the shelf is raised above the taskbar/dock layer on Windows
        # before animating it into view.
        self.show()
        self.raise_()
        self._set_history_loading(self._history_loading)

        if SHELF_CHIP_REVEAL_ENABLED:
            self.reveal_chips()
        self.animate_to(self.open_pos)

    def hide_shelf(self, force=False):
        if self.is_shelf_pinned and not force:
            return

        popup = self._active_chip_context_menu()
        if popup is not None:
            fade(popup, 1.0, 0.0, CHIP_CONTEXT_MENU_FADE_OUT_MS, finished=popup.close)

        self.is_open = False
        self._set_history_loading(self._history_loading)
        self._is_hiding = True
        if self.hide_reset_timer.isActive():
            self.hide_reset_timer.stop()
        self.hide_reset_timer.start(max(MOTION_SHELF_MS, 120) + 40)

        self.animate_to(self.hidden_pos)

    def reveal_chips(self):
        # Animations removed: ensure all chips are visible immediately
        for index in range(self.chip_layout.count()):
            item = self.chip_layout.itemAt(index)
            chip = item.widget() if item else None
            if chip is None or chip is getattr(self, "empty_state_widget", None):
                continue
            chip.setVisible(True)
            if hasattr(chip, "_base_width"):
                chip.setMinimumWidth(chip._base_width)
                chip.setMaximumWidth(chip._base_width)

    def toggle_shelf_pin(self):
        self.is_shelf_pinned = not self.is_shelf_pinned
        if self.is_shelf_pinned:
            if self.auto_hide_timer.isActive():
                self.auto_hide_timer.stop()
            self.show_shelf("active")
        else:
            self.hide_shelf(force=True)

    @safe_slot("Failed to check toggle hotkey")
    def check_toggle_hotkey(self):
        is_down = self.is_toggle_hotkey_down()
        if is_down and not self._hotkey_was_down:
            self.toggle_shelf_pin()
        self._hotkey_was_down = is_down

    @safe_slot("Failed to inspect toggle hotkey")
    def is_toggle_hotkey_down(self):
        if sys.platform != "win32":
            return False

        ctrl_pressed = (
            ctypes.windll.user32.GetAsyncKeyState(0x11) & 0x8000
            or ctypes.windll.user32.GetAsyncKeyState(0xA2) & 0x8000
            or ctypes.windll.user32.GetAsyncKeyState(0xA3) & 0x8000
        )
        win_pressed = (
            ctypes.windll.user32.GetAsyncKeyState(0x5B) & 0x8000
            or ctypes.windll.user32.GetAsyncKeyState(0x5C) & 0x8000
        )
        return bool(ctrl_pressed and win_pressed)

    def animate_to(self, target):
        if self._target_pos == target:
            return

        self._target_pos = target
        if not MOTION_ENABLED:
            self.move(target)
            return

        self.animation.stop()
        self.animation.setStartValue(self.pos())
        self.animation.setEndValue(target)
        self.animation.start()

    def update_screen_geometry(self, monitor_hint="cursor"):
        screen = self.screen_for_hint(monitor_hint)
        geometry = screen.availableGeometry()
        full_geometry = screen.geometry()
        cache_key = (
            screen.name(),
            geometry.left(),
            geometry.top(),
            geometry.width(),
            geometry.height(),
            full_geometry.left(),
            full_geometry.top(),
            full_geometry.width(),
            full_geometry.height(),
        )
        if cache_key == self._screen_geometry_cache_key:
            return

        self._screen_geometry_cache_key = cache_key
        width = max(720, int(geometry.width() * self.shelf_width_ratio))
        width = min(width, geometry.width() - 32)

        shelf_height = int(self.theme.get("shelf", {}).get("height", 52))
        shelf_top_margin = int(self.theme.get("shelf", {}).get("top_margin", 6))
        window_width = width + self._shadow_margin * 2
        window_height = shelf_height + self._shadow_margin * 2
        window_size = QSize(window_width, window_height)
        if self.size() != window_size:
            self.setFixedSize(window_size)

        x = geometry.left() + (geometry.width() - width) // 2 - self._shadow_margin
        y = geometry.top() + shelf_top_margin - self._shadow_margin
        self.screen_geometry = geometry
        self.full_screen_geometry = full_geometry
        self.open_pos = QPoint(x, y)
        hidden_y = full_geometry.top() - self.height() - 10
        self.hidden_pos = QPoint(x, hidden_y)
        trigger_center = geometry.left() + geometry.width() // 2
        trigger_half_width = HOVER_TRIGGER_WIDTH // 2
        self.trigger_left = trigger_center - trigger_half_width
        self.trigger_right = trigger_center + trigger_half_width

    def screen_for_hint(self, monitor_hint):
        return (
            QApplication.primaryScreen()
            or QApplication.screenAt(QCursor.pos())
            or self.active_window_screen()
        )

    def active_window_screen(self):
        if not sys.platform.startswith("win"):
            return None

        hwnd = self.paste_controller.foreground_window()
        if not hwnd:
            return None

        rect = ctypes.wintypes.RECT()
        if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None

        center = QPoint((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
        return QApplication.screenAt(center)

    def shutdown(self):
        try:
            self.clipboard_manager.close()
        except Exception:
            log_exception("Failed to shut down clipboard manager")
        try:
            shutdown_favicon_service()
        except Exception:
            log_exception("Failed to shut down favicon service")
