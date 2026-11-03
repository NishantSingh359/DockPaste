"""Shared layout, typography, and shape configuration for all DockPaste UI.

Use this file for dimensions and non-color styling across settings, tray menus,
the shelf, clips, context menus, previews, and notifications. Theme JSON files
provide colors only.
"""

import sys
from pathlib import Path

# Settings window geometry and typography.
WINDOW_TITLE = "Settings"
WINDOW_SIZE = (1000, 900)
WINDOW_MIN_SIZE = (900, 770)
ROOT_MARGINS = (12, 12, 12, 12)
ROOT_SPACING = 12
FONT_FAMILY = "Inter"
_BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
FONT_FILE = _BUNDLE_ROOT / "assets" / "fonts" / "Inter-Variable.ttf"
APP_ICON_FILE = _BUNDLE_ROOT / "assets" / "app_icons" / "DockPaste.ico"

# Shared text metrics.
FONT = {
    "dialog_size": 13,
    "sidebar_size": 14,
    "sidebar_weight": 500,
    "page_title_size": 30,
    "page_title_weight": 700,
    "page_subtitle_size": 18,
    "page_subtitle_weight": 500,
    "setting_title_size": 20,
    "setting_title_weight": 400,
    "setting_description_size": 15,
    "setting_description_weight": 500,
    "control_size": 16,
    "control_weight": 500,
}

# Settings navigation, pages, and cards.
SIDEBAR_WIDTH = 260
SIDEBAR_PANEL_INSET = 8
SIDEBAR_PANEL_MARGINS = (SIDEBAR_PANEL_INSET,) * 4
SIDEBAR_PANEL_RADIUS = 16
SIDEBAR_SPACING = 4
SIDEBAR_PADDING = (18, 10)
NAV_ITEM_MARGINS = (2, 3, 2, 3)
NAV_ITEM_SIZE = (
    SIDEBAR_WIDTH - 2 * SIDEBAR_PANEL_INSET - 2 * SIDEBAR_PADDING[1] - 2 * NAV_ITEM_MARGINS[1],
    46,
)
NAV_ROW_MARGINS = (10, 0, 8, 0)
NAV_ROW_SPACING = 12
NAV_ICON_SIZE = 24
NAV_ICON_VIEWBOX_SIZE = 24
NAV_ICON_STROKE_WIDTH = 2
NAV_ROW_INSET = (2, 1, -2, -1)
NAV_ROW_RADIUS = 8

PAGE_MARGINS = (30, 26, 30, 28)
PAGE_SPACING = 6
PAGE_DESCRIPTION_GAP = 16
CARD_MARGINS = (16, 4, 16, 4)
CARD_ROW_SPACING = 0
CARD_RADIUS = 12
SETTING_ROW_MARGINS = (0, 11, 0, 11)
SETTING_ROW_SPACING = 18
SETTING_TEXT_SPACING = 3
SETTING_TEXT_MARGINS = (0, 0, 0, 0)
ROW_SEPARATOR_HEIGHT = 1
CONTROL_MIN_WIDTH = 150
CONTROL_RADIUS = 8
CONTROL_PADDING = (7, 10)
CONTROL_MIN_HEIGHT = 18
SUBTITLE_BOTTOM_PADDING = 2
SHELF_WIDTH_DECIMALS = 2
SHELF_WIDTH_STEP = 0.01

# Settings controls and feedback elements.
CLEAR_BUTTON_RADIUS = 8
CLEAR_BUTTON_PADDING = (8, 12)
CONFIRMATION_BUTTON_RADIUS = 7
CONFIRMATION_BUTTON_PADDING = (7, 14)
CONFIRMATION_BUTTON_MIN_WIDTH = 76
CONFIRMATION_BUTTON_WEIGHT = 500
SETTINGS_PANEL_BORDER_WIDTH = 1
SETTINGS_CARD_BORDER_WIDTH = 1
CONTROL_BORDER_WIDTH = 1
CONTROL_FOCUS_BORDER_WIDTH = 1
BUTTON_BORDER_WIDTH = 1

# Shared scrolling, switches, and dropdowns.
SCROLLBAR_WIDTH = 12
SCROLLBAR_MARGIN = (4, 3)
SCROLLBAR_HANDLE_MIN_HEIGHT = 36
SCROLLBAR_RADIUS = 6
SETTINGS_SCROLL_STEP = 28
HISTORY_RENDER_BATCH_SIZE = 3
HISTORY_RENDER_INTERVAL_MS = 8
HISTORY_RENDER_PAGE_SIZE = 32

SWITCH_SIZE = (42, 24)
SWITCH_TRACK_RADIUS = 11
SWITCH_THUMB_SIZE = 18
SWITCH_THUMB_X = {"off": 3, "on": 21}
SWITCH_INSET = 1
SWITCH_BORDER_WIDTH = 1
SWITCH_HOVER_LIGHTEN = 115
SWITCH_ANIMATION_MS = 150

# Semantic settings navigation icon paths.
NAV_ICON_PATHS = {
    "general": (
        '<path d="M4 6h16M4 12h16M4 18h16"/>'
        '<circle cx="9" cy="6" r="2"/><circle cx="15" cy="12" r="2"/>'
        '<circle cx="8" cy="18" r="2"/>'
    ),
    "appearance": (
        '<path d="M12 3a9 9 0 1 0 0 18h1.4a2 2 0 0 0 1.4-3.4 '
        '1.7 1.7 0 0 1 1.2-2.9H18a3 3 0 0 0 3-3c0-4.8-4-8.7-9-8.7z"/>'
        '<circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7.5" r="1"/>'
        '<circle cx="15" cy="8" r="1"/>'
    ),
    "history": (
        '<path d="M3 12a9 9 0 1 0 2.6-6.4L3 8"/><path d="M3 3v5h5"/>'
        '<path d="M12 7v5l3 2"/>'
    ),
    "support": (
        '<path d="M20.8 8.8c0 5.2-8.8 10.2-8.8 10.2S3.2 14 3.2 8.8A4.3 4.3 0 0 1 11 6.1l1 1.1 1-1.1a4.3 4.3 0 0 1 7.8 2.7z"/>'
    ),
    "about": (
        '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/>'
        '<path d="M12 8h.01" stroke-width="3"/>'
    ),
}

THEME_PICKER = {
    "card_margins": (22, 20, 22, 22),
    "option_size": (166, 126),
    "preview_inset": 7,
    "preview_height": 78,
    "preview_radius": 9,
    "preview_panel_inset": 10,
    "preview_panel_radius": 8,
    "preview_accent_size": 20,
    "preview_accent_radius": 5,
    "option_radius": 11,
    "option_label_size": 13,
    "row_spacing": 14,
    "selected_badge_size": 14,
    "section_title_size": 23,
    "section_title_weight": 500,
    "section_gap": 12,
    "accent_section_gap": 18,
}
SHELF_POSITION_PICKER = {
    "card_margins": (22, 20, 22, 22),
    "option_size": THEME_PICKER["option_size"],
    "preview_inset": THEME_PICKER["preview_inset"],
    "preview_height": THEME_PICKER["preview_height"],
    "preview_radius": THEME_PICKER["preview_radius"],
    "option_radius": THEME_PICKER["option_radius"],
    "label_size": THEME_PICKER["option_label_size"],
    "selected_badge_size": THEME_PICKER["selected_badge_size"],
    "row_spacing": THEME_PICKER["row_spacing"],
    "screen_inset": 12,
    "screen_radius": 7,
    "shelf_width": 50,
    "shelf_height": 6,
    "shelf_radius": 3,
    "section_gap": 12,
}
ACCENT_PICKER = {
    "option_size": (66, 68),
    "swatch_size": 40,
    "swatch_top": 5,
    "ring_inset": 4,
    "border_width": 2,
    "row_spacing": 12,
    "label_size": 10,
    "label_gap": 5,
}
ACCENT_LABELS = (
    "Blue",
    "Purple",
    "Indigo",
    "Amber",
    "Jade",
    "Leaf Green",
    "Teal",
)


# Shared non-color appearance settings for the shelf and its contents.
# Theme JSON files supply all color values.
SHELF = {
    "height": 52,
    "top_margin": 6,
    "padding": (9, 0, 9, 0),
    "margin": (0, 0, 0, 0),
    "spacing": 5,
    "chip_spacing": 10,
    "filter_spacing": 10,
    "filter_icon_size": 22,
    "border_width": 2,
    "border_radius": 27,
    "shadow_blur_radius": 10,
    "shadow_offset": (0, 1),
    "width_ratio": 0.7,
    "width_ratio_min": 0.30,
    "width_ratio_max": 0.98,
}

CHIP = {
    "height": 32,
    "minimum_width": 70,
    "maximum_width": 350,
    "minimum_width_limit": 70,
    "maximum_width_limit": 550,
    "padding": (10, 0, 10, 0),
    "spacing": 8,
    "border_radius": 15,
    "border_width": 1,
    "font_size": 15,
    "font_weight": 500,
    "icon_font_weight": 800,
    "index_font_size": 11,
    "index_font_weight": 700,
    "icon_size": 18,
    "pinned_indicator_size": 8,
    "icon_font_size": 11,
    "open_icon_path": "assets/icons/open_link.svg",
    "open_icon_size": 18,
    "folder_icon_path": "assets/icons/folder.svg",
    "file_icon_path": "assets/icons/file.svg",
    "favicon_size": 22,
    "folder_icon_size": 22,
    "color_preview_size": 22,
    "color_preview_border_width": 0,
    "thumbnail": {
        "width": 48,
        "height": 26,
        "border_radius": 6,
        "shadow_blur_radius": 6,
        "shadow_offset": (0, 1),
    },
}

CONTEXT_MENU = {
    "border_width": 2,
    "border_radius": 50,
    "padding": 6,
    "item_size": 16,
    "item_padding": 5,
    "item_margin": 2,
    "item_border_radius": 7,
    "icon_size": 18,
    "icon_stroke_width": 2,
    "pin_icon": '<path d=\"M12 17v5\"/><path d=\"M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z\"/>',
    "unpin_icon": '<path d="M12 17v5"/><path d="M15 9.34V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H7.89"/><path d="m2 2 20 20"/><path d="M9 9v1.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h11"/>',
    "copy_icon": '<rect x="8" y="7" width="11" height="13" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h2"/>',
    "delete_icon": '<path d="M10 11v6"/><path d="M14 11v6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    "clear_icon": '<path d="m16 22-1-4"/><path d="M19 14a1 1 0 0 0 1-1v-1a2 2 0 0 0-2-2h-3a1 1 0 0 1-1-1V4a2 2 0 0 0-4 0v5a1 1 0 0 1-1 1H6a2 2 0 0 0-2 2v1a1 1 0 0 0 1 1"/><path d="M19 14H5l-1.973 6.767A1 1 0 0 0 4 22h16a1 1 0 0 0 .973-1.233z"/><path d="m8 22 1-4"/>',
}

EMPTY_STATE = {
    "text": "Nothing Here",
    "font_size": 17,
    "font_weight": 600,
    "padding": (5, 12),
    "left_padding": 15,
    "icon_enabled": True,
    "icon_path": "assets/icons/clear.svg",
    "icon_size": 22,
    "icon_spacing": 5,
}

PREVIEW = {
    "minimum_height": 66,
    "border_width": 1,
    "border_radius": 12,
    "padding": (10, 12),
    "font_size": 13,
}
TEXT_PREVIEW = {
    "font_family": "Inter",
    "font_size": 13,
    "padding": (12, 12, 12, 12),
    "text_padding": 8,
    "max_width_ratio": 0.85,
    "max_height_ratio": 0.85,
    "min_width": 420,
    "min_height": 190,
    "max_min_width": 360,
    "max_min_height": 240,
    "measurement_sample_length": 20000,
    "measurement_max_columns": 100,
    "measurement_min_columns": 40,
    "measurement_max_lines": 100,
    "horizontal_padding_allowance": 72,
    "vertical_padding_allowance": 100,
}
SCROLL_VIEWPORT = {
    "border_radius": 40,
    "edge_fade": {
        "enabled": True,
        "width": 40,
        "alpha_stops": ((0.0, 0.0), (0.35, 0.2), (0.7, 0.7), (1.0, 1.0)),
    },
}
NOTIFICATION = {
    "title_font_size": 14,
    "title_font_weight": 600,
    "message_font_size": 12,
    "message_font_weight": 400,
    "border_radius": 12,
    "padding": (12, 16),
    "width": 360,
    "duration_ms": 4500,
    "border_width": 1,
    "card_spacing": 12,
    "accent_bar_width": 4,
    "text_spacing": 3,
    "accent_radius": 2,
    "screen_edge_margin": 20,
}
THEME_LAYOUT = {
    "shelf": SHELF,
    "chip": CHIP,
    "context_menu": CONTEXT_MENU,
    "empty": EMPTY_STATE,
    "preview": PREVIEW,
    "text_preview": TEXT_PREVIEW,
    "scroll_viewport": SCROLL_VIEWPORT,
    "notification": NOTIFICATION,
}
TRAY_MENU = {
    "width": 120,
    "icon_size": 22,
    "icon_stroke_width": 2.2,
    "radius": 10,
    "border_width": 1,
    "font_family": "Inter, 'Segoe UI', sans-serif",
    "font_size": 15,
    "font_weight": 600,
    "padding": (2, 2),
    "item_padding": (4, 4),
    "item_content_left_padding": 6,
    "item_margin": (3, 3),
    "item_radius": 7,
    "item_min_width": 64,
    "separator_height": 1,
    "separator_margins": (4, 8),
}


def component(section, key, default=None):
    """Read a shared non-color UI value."""
    return globals().get(section, {}).get(key, default)

# Settings stylesheet builders. Colors are supplied by the active theme.
def settings_stylesheet(palette):
    p = palette
    f = FONT
    scrollbar_track = p.get("scrollbar_track", p["control_background"])
    scrollbar_thumb = p.get("scrollbar_thumb", p["secondary_text"])
    scrollbar_thumb_hover = p.get("scrollbar_thumb_hover", p["accent"])
    return f"""
        QDialog {{ background: {p['background']}; color: {p['text']}; font-family: {FONT_FAMILY}; font-size: {f['dialog_size']}px; }}
        QDialog QWidget {{ font-family: {FONT_FAMILY}; }}
        QStackedWidget#settingsPages {{ background: {p['background']}; }}
        QScrollArea#settingsPageScroll {{ background: {p['background']}; border: none; }}
        QWidget#settingsPage {{ background: {p['background']}; }}
        QFrame#settingsControlPanel {{ background: {p['surface']}; border: {SETTINGS_PANEL_BORDER_WIDTH}px solid {p['border']}; border-radius: {SIDEBAR_PANEL_RADIUS}px; }}
        QListWidget#settingsSidebar, QListWidget#settingsSidebar::viewport {{ background: transparent; border: none; }}
        QListWidget#settingsSidebar {{ padding: {SIDEBAR_PADDING[0]}px {SIDEBAR_PADDING[1]}px; outline: none; }}
        QListWidget#settingsSidebar::item {{ background: transparent; border: none; padding: 0; margin: {NAV_ITEM_MARGINS[0]}px {NAV_ITEM_MARGINS[1]}px; }}
        QWidget#settingsNavRow {{ background: transparent; border-radius: {NAV_ROW_RADIUS}px; }}
        QLabel#settingsNavLabel {{ color: {p['text']}; font-weight: {f['sidebar_weight']}; }}
        QLabel#pageHeading {{ color: {p['text']}; font-size: {f['page_title_size']}px; font-weight: {f['page_title_weight']}; }}
        QLabel#pageSubtitle {{ color: {p['secondary_text']}; font-size: {f['page_subtitle_size']}px; font-weight: {f['page_subtitle_weight']}; padding-bottom: {SUBTITLE_BOTTOM_PADDING}px; }}
        QLabel#appearanceSectionTitle {{ color: {p['text']}; font-size: {THEME_PICKER['section_title_size']}px; font-weight: {THEME_PICKER['section_title_weight']}; }}
        QLabel#aboutAppName {{ color: {p['text']}; font-size: 28px; font-weight: 700; }}
        QLabel#aboutAppIcon {{ background: {p['control_background']}; border: {SETTINGS_CARD_BORDER_WIDTH}px solid {p['border']}; border-radius: 16px; }}
        QLabel#aboutVersionBadge {{ color: {p['accent']}; background: {p['control_background']}; border: {BUTTON_BORDER_WIDTH}px solid {p['control_border']}; border-radius: 10px; padding: 5px 10px; font-size: {f['dialog_size']}px; font-weight: 600; }}
        QLabel#aboutFactValue {{ color: {p['text']}; font-size: {f['control_size']}px; font-weight: {f['control_weight']}; }}
        QFrame#settingsCard {{ background: {p['surface']}; border: {SETTINGS_CARD_BORDER_WIDTH}px solid {p['border']}; border-radius: {CARD_RADIUS}px; }}
        QLabel#browseDateTitle {{ color: {p['text']}; font-size: {f['setting_title_size']}px; font-weight: {f['setting_title_weight']}; }}
        QLabel#browseDateDescription {{ color: {p['secondary_text']}; font-size: {f['setting_description_size']}px; font-weight: {f['setting_description_weight']}; }}
        QLabel#browseDateValue {{ color: {p['text']}; font-size: 16px; font-weight: 500; padding-right: 2px; }}
        QFrame#rowSeparator {{ background: {p['border']}; border: none; }}
        QPushButton#clearHistoryButton {{ color: {p['danger']}; background: {p['control_background']}; border: {BUTTON_BORDER_WIDTH}px solid {p['border']}; border-radius: {CLEAR_BUTTON_RADIUS}px; padding: {CLEAR_BUTTON_PADDING[0]}px {CLEAR_BUTTON_PADDING[1]}px; font-size: {f['control_size']}px; font-weight: {f['control_weight']}; }}
        QPushButton#clearHistoryButton:hover {{ background: {p['control_hover_background']}; border-color: {p['danger']}; }}
        QPushButton#clearHistoryButton:pressed {{ background: {p['surface_hover']}; }}
        QPushButton#supportLinkButton {{ color: {p['text']}; background: {p['control_background']}; border: {BUTTON_BORDER_WIDTH}px solid {p['control_border']}; border-radius: {CONTROL_RADIUS}px; padding: {CLEAR_BUTTON_PADDING[0]}px {CLEAR_BUTTON_PADDING[1]}px; font-size: {f['control_size']}px; font-weight: {f['control_weight']}; }}
        QPushButton#supportLinkButton:hover {{ background: {p['control_hover_background']}; border-color: {p['control_hover_border']}; }}
        QPushButton#supportLinkButton:pressed {{ background: {p['surface_hover']}; }}
        QLabel#settingTitle {{ color: {p['text']}; font-size: {f['setting_title_size']}px; font-weight: {f['setting_title_weight']}; }}
        QLabel#settingDescription {{ color: {p['secondary_text']}; font-size: {f['setting_description_size']}px; font-weight: {f['setting_description_weight']}; }}
        QCheckBox#settingsSwitch {{ background: transparent; border: none; }}
        QComboBox, QSpinBox, QDoubleSpinBox {{ color: {p['text']}; background: {p['control_background']}; border: {CONTROL_BORDER_WIDTH}px solid {p['control_border']}; border-radius: {CONTROL_RADIUS}px; padding: {CONTROL_PADDING[0]}px {CONTROL_PADDING[1]}px; min-height: {CONTROL_MIN_HEIGHT}px; font-size: {f['control_size']}px; font-weight: {f['control_weight']}; selection-background-color: {p['accent']}; selection-color: {p['white']}; }}
        QSlider#historyDateSlider {{ min-width: 180px; min-height: 64px; }}
        QSlider#historyDateSlider::groove:horizontal {{ height: 12px; background: transparent; }}
        QSlider#historyDateSlider::sub-page:horizontal, QSlider#historyDateSlider::add-page:horizontal {{ background: transparent; }}
        QSlider#historyDateSlider::handle:horizontal {{ width: 44px; margin: -16px 0; background: transparent; border: none; }}
        QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ color: {p['text']}; background: {p['control_hover_background']}; border-color: {p['control_hover_border']}; }}
        QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: {CONTROL_FOCUS_BORDER_WIDTH}px solid {p['control_focus_border']}; }}
        QLineEdit, QSpinBox QLineEdit, QDoubleSpinBox QLineEdit {{ color: {p['text']}; selection-background-color: {p['accent']}; selection-color: {p['white']}; font-weight: {f['control_weight']}; }}
        QScrollBar:vertical {{ background: {scrollbar_track}; width: {SCROLLBAR_WIDTH}px; margin: {SCROLLBAR_MARGIN[0]}px {SCROLLBAR_MARGIN[1]}px; border-radius: {SCROLLBAR_RADIUS}px; }}
        QScrollBar::handle:vertical {{ background: {scrollbar_thumb}; min-height: {SCROLLBAR_HANDLE_MIN_HEIGHT}px; border-radius: {SCROLLBAR_RADIUS}px; margin: 1px; }}
        QScrollBar::handle:vertical:hover, QScrollBar::handle:vertical:pressed {{ background: {scrollbar_thumb_hover}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        QScrollBar:horizontal {{ height: 0; margin: 0; }}
    """


def confirmation_stylesheet(palette):
    p = palette
    return f"""
        QMessageBox {{ background: {p['background']}; color: {p['text']}; font-family: {FONT_FAMILY}; font-size: {FONT['dialog_size']}px; }}
        QMessageBox QLabel {{ color: {p['text']}; font-family: {FONT_FAMILY}; font-size: {FONT['dialog_size']}px; }}
        QMessageBox QPushButton {{ color: {p['text']}; background: {p['surface']}; border: {BUTTON_BORDER_WIDTH}px solid {p['border']}; border-radius: {CONFIRMATION_BUTTON_RADIUS}px; padding: {CONFIRMATION_BUTTON_PADDING[0]}px {CONFIRMATION_BUTTON_PADDING[1]}px; min-width: {CONFIRMATION_BUTTON_MIN_WIDTH}px; font-family: {FONT_FAMILY}; font-size: {FONT['dialog_size']}px; font-weight: {CONFIRMATION_BUTTON_WEIGHT}; }}
        QMessageBox QPushButton:hover {{ background: {p['surface_hover']}; }}
        QMessageBox QPushButton:focus {{ border-color: {p['control_focus_border']}; outline: none; }}
        QMessageBox QPushButton#confirmClearButton {{ color: {p['danger']}; }}
    """
