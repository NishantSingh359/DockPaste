import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from config import BASE_DIR
from ui_config import THEME_LAYOUT


THEME_DIR = BASE_DIR / "themes"
DEFAULT_THEME = "dark"
LEGACY_THEME_NAMES = {"one_dark_pro_night_flat": "dark_pro"}
_CSS_COLOR = re.compile(
    r"^(?:#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})|rgba?\([\d.%\s,]+\)|transparent|black|white)$"
)


class ThemeManager:
    """Loads color-only themes and combines them with shared UI layout config."""

    def __init__(self, theme_dir=THEME_DIR):
        self.theme_dir = Path(theme_dir)
        self._themes = {}
        self._load_themes()

    def _load_themes(self):
        self._themes = {}
        if not self.theme_dir.is_dir():
            return

        loaded = {}
        for theme_file in sorted(self.theme_dir.glob("*.json")):
            try:
                with theme_file.open("r", encoding="utf-8") as source:
                    theme = json.load(source)
                if not isinstance(theme, dict):
                    continue
                name = str(theme.get("name", theme_file.stem)).lower()
                if name and isinstance(theme.get("display_name"), str):
                    loaded[name] = theme
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue

        default = loaded.get(DEFAULT_THEME)
        if default is None and loaded:
            default = next(iter(loaded.values()))
        if default is None:
            return
        palette_schema = {
            key: value
            for key, value in default.items()
            if key not in {"name", "display_name"}
        }
        for name, theme in loaded.items():
            sanitized = self._sanitize_palette(theme, palette_schema)
            self._themes[name] = {
                "name": name,
                "display_name": theme["display_name"],
                **sanitized,
            }

    def available_themes(self):
        return [
            (name, theme.get("display_name", name.title()))
            for name, theme in sorted(self._themes.items())
        ]

    def get_theme(self, name):
        theme_name = str(name or DEFAULT_THEME).lower()
        theme_name = LEGACY_THEME_NAMES.get(theme_name, theme_name)
        default_name = self._themes_default_name()
        if theme_name not in self._themes:
            theme_name = default_name
        theme = deepcopy(THEME_LAYOUT)
        self._merge_values(theme, self._themes[default_name])
        self._merge_values(theme, self._themes[theme_name])
        return {**theme, "name": theme_name}

    def _themes_default_name(self):
        return DEFAULT_THEME if DEFAULT_THEME in self._themes else next(iter(self._themes))

    @classmethod
    def _sanitize_palette(cls, values, schema):
        """Keep theme files limited to known color tokens and valid color values."""
        sanitized = {}
        for key, expected in schema.items():
            value = values.get(key)
            if isinstance(expected, str):
                if isinstance(value, str) and _CSS_COLOR.fullmatch(value.strip()):
                    sanitized[key] = value
            elif isinstance(expected, list):
                if isinstance(value, list) and all(
                    isinstance(item, str) and _CSS_COLOR.fullmatch(item.strip())
                    for item in value
                ):
                    sanitized[key] = value
            elif isinstance(expected, dict) and isinstance(value, dict):
                nested = cls._sanitize_palette(value, expected)
                if nested:
                    sanitized[key] = nested
        return sanitized

    @staticmethod
    def with_accent_color(theme, color):
        """Return a themed palette with the selected accent applied consistently."""
        themed = deepcopy(theme)
        for section, key in (
            ("settings", "accent"),
            ("chip", "folder_icon_color"),
            ("context_menu", "destructive_icon_color"),
            ("text_preview", "selection"),
            ("notification", "accent"),
            ("tray_menu", "accent"),
        ):
            if key in themed.get(section, {}):
                themed[section][key] = color
        return themed

    @staticmethod
    def _merge_values(target, values):
        for key, value in values.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                ThemeManager._merge_values(target[key], value)
            else:
                # Do not retain references into cached theme dictionaries.
                # Merging a selected theme into the default palette would
                # otherwise overwrite the default theme's nested color maps.
                target[key] = deepcopy(value)

    def is_valid(self, name):
        normalized = str(name or "").lower()
        normalized = LEGACY_THEME_NAMES.get(normalized, normalized)
        return normalized in self._themes

    def get(self, theme, section, key, default=None):
        value = self.get_theme(theme).get(section, {}).get(key, default)
        return value

    @staticmethod
    def theme_values(theme):
        """Return the current theme's palette values for the UI modules."""
        return theme


THEME_MANAGER = ThemeManager()
THEME_MANAGER.active_theme = DEFAULT_THEME


def get_theme_value(theme, section, key, default=None):
    return theme.get(section, {}).get(key, default)


def set_active_theme(name):
    theme = THEME_MANAGER.get_theme(name)
    THEME_MANAGER.active_theme = theme["name"]
    return theme
