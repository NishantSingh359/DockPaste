"""Validated persistence for DockPaste's user-facing settings."""

import json
import math
from dataclasses import dataclass
from pathlib import Path

from animation_config import CHIP_SCROLL_SPEED, CHIP_SCROLL_SPEED_MAX, CHIP_SCROLL_SPEED_MIN
from config import (
    CHIP_MAX_WIDTH,
    CHIP_MIN_WIDTH,
    CHIP_WIDTH_DEFAULTS_VERSION,
    CHIP_WIDTH_MAX_LIMIT,
    CHIP_WIDTH_MIN_LIMIT,
    CLIPBOARD_HISTORY_RETENTION_DAYS,
    CLIPBOARD_HISTORY_RETENTION_MAX_DAYS,
    CLIPBOARD_HISTORY_RETENTION_MIN_DAYS,
    HIDE_ON_PASTE,
    SHELF_SHOW_ON_HOVER,
    SHELF_WIDTH_RATIO,
    SHELF_WIDTH_RATIO_MAX,
    SHELF_WIDTH_RATIO_MIN,
    clip_indexing,
    COLOR_PREVIEW_ENABLED,
)
from utils.app_logging import log_exception


@dataclass(frozen=True)
class SettingSpec:
    """Type and bounds for one persisted setting."""

    kind: type
    default: object
    minimum: float | None = None
    maximum: float | None = None

    def normalize(self, value):
        if self.kind is bool:
            return value if isinstance(value, bool) else self.default
        if self.kind is int:
            if isinstance(value, bool) or not isinstance(value, int):
                return self.default
            normalized = value
        elif self.kind is float:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return self.default
            normalized = float(value)
            if not math.isfinite(normalized):
                return self.default
        elif self.kind is str:
            return value if isinstance(value, str) else self.default
        else:
            return self.default

        if self.minimum is not None:
            normalized = max(self.minimum, normalized)
        if self.maximum is not None:
            normalized = min(self.maximum, normalized)
        return normalized


SETTING_SPECS = {
    "show_on_hover_enabled": SettingSpec(bool, SHELF_SHOW_ON_HOVER),
    "hide_on_paste_enabled": SettingSpec(bool, HIDE_ON_PASTE),
    "highlight_shelf_on_drag_enabled": SettingSpec(bool, True),
    "clip_scroll_speed": SettingSpec(
        int, CHIP_SCROLL_SPEED, CHIP_SCROLL_SPEED_MIN, CHIP_SCROLL_SPEED_MAX
    ),
    "clip_indexing_enabled": SettingSpec(bool, clip_indexing),
    "color_preview_enabled": SettingSpec(bool, COLOR_PREVIEW_ENABLED),
    "text_preview_on_double_click_enabled": SettingSpec(bool, False),
    "open_images_on_double_click_enabled": SettingSpec(bool, True),
    "prevent_oversize_items_enabled": SettingSpec(bool, True),
    "show_oversize_warning_enabled": SettingSpec(bool, True),
    "close_to_tray_enabled": SettingSpec(bool, True),
    "start_with_windows_enabled": SettingSpec(bool, False),
    "chip_min_width": SettingSpec(
        int, CHIP_MIN_WIDTH, CHIP_WIDTH_MIN_LIMIT, CHIP_WIDTH_MAX_LIMIT
    ),
    "chip_max_width": SettingSpec(
        int, CHIP_MAX_WIDTH, CHIP_WIDTH_MIN_LIMIT, CHIP_WIDTH_MAX_LIMIT
    ),
    "history_retention_days": SettingSpec(
        int,
        CLIPBOARD_HISTORY_RETENTION_DAYS,
        CLIPBOARD_HISTORY_RETENTION_MIN_DAYS,
        CLIPBOARD_HISTORY_RETENTION_MAX_DAYS,
    ),
    "shelf_width_ratio": SettingSpec(
        float, SHELF_WIDTH_RATIO, SHELF_WIDTH_RATIO_MIN, SHELF_WIDTH_RATIO_MAX
    ),
    "theme": SettingSpec(str, "dark"),
    "accent_color": SettingSpec(str, "#007AFF"),
    "chip_width_defaults_version": SettingSpec(
        int, 0, 0, CHIP_WIDTH_DEFAULTS_VERSION
    ),
}


class UserSettingsStore:
    """Load, validate, and atomically save the app's persisted preferences."""

    def __init__(self, path):
        self.path = Path(path)

    @staticmethod
    def normalize(values):
        values = values if isinstance(values, dict) else {}
        normalized = {
            key: spec.normalize(values.get(key, spec.default))
            for key, spec in SETTING_SPECS.items()
        }
        if normalized["chip_max_width"] < normalized["chip_min_width"]:
            normalized["chip_max_width"] = normalized["chip_min_width"]
        if not normalized["prevent_oversize_items_enabled"]:
            normalized["show_oversize_warning_enabled"] = False
        return normalized

    def load(self):
        try:
            with self.path.open("r", encoding="utf-8") as settings_file:
                raw = json.load(settings_file)
        except FileNotFoundError:
            raw = {}
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            log_exception(f"Failed to load user settings: {exc}")
            raw = {}
        return self.normalize(raw)

    def save(self, values):
        normalized = self.normalize(values)
        temporary_path = self.path.with_name(f".{self.path.name}.tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with temporary_path.open("w", encoding="utf-8") as settings_file:
                json.dump(normalized, settings_file, indent=2)
                settings_file.flush()
            temporary_path.replace(self.path)
            return normalized
        except (OSError, TypeError, ValueError) as exc:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            log_exception(f"Failed to save user settings: {exc}")
            return self.normalize({})
