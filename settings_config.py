"""Visual configuration for the DockPaste Settings window.

Keep these values separate from the shelf themes so Settings stays visually
consistent when the user changes the appearance of the shelf.
"""

import sys
from pathlib import Path

WINDOW_TITLE = "Settings"
WINDOW_SIZE = (900, 770)
WINDOW_MIN_SIZE = (900, 770)
WINDOW_MAX_SIZE = (1100, 1000)
ROOT_MARGINS = (0, 0, 0, 0)
ROOT_SPACING = 0
FONT_FAMILY = "Inter"
_BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
FONT_FILE = _BUNDLE_ROOT / "assets" / "fonts" / "Inter-Variable.ttf"

PALETTE = {
    "background": "#141414",
    "surface": "#232323",
    "surface_hover": "#2E2E31",
    "border": "#333333",
    "control_background": "#212121",
    "control_hover_background": "#212121",
    "control_border": "#303030",
    "control_hover_border": "#303030",
    "control_focus_border": "#55555A",
    "text": "#F5F5F7",
    "secondary_text": "#A1A1A6",
    "accent": "#0071E3",
    "white": "#D4D4D4",
    "switch_off": "#505050",
    "switch_disabled": "#323232",
    "disabled_thumb": "#B8B9BC",
}

FONT = {
    "dialog_size": 13,
    "sidebar_size": 14,
    "sidebar_weight": 500,
    "page_title_size": 30,
    "page_title_weight": 700,
    "page_subtitle_size": 16,
    "page_subtitle_weight": 600,
    "setting_title_size": 20,
    "setting_title_weight": 600,
    "setting_description_size": 14,
    "setting_description_weight": 600,
    "control_size": 16,
    "control_weight": 600,
}

SIDEBAR_WIDTH = 230
SIDEBAR_SPACING = 4
SIDEBAR_PADDING = (18, 10)
NAV_ITEM_SIZE = (206, 46)
NAV_ROW_MARGINS = (10, 0, 8, 0)
NAV_ROW_SPACING = 12
NAV_ICON_SIZE = 24
NAV_ICON_VIEWBOX_SIZE = 24
NAV_ICON_STROKE_WIDTH = 2
NAV_ROW_INSET = (2, 1, -2, -1)
NAV_ROW_RADIUS = 8
NAV_ITEM_MARGINS = (2, 3, 2, 3)

PAGE_MARGINS = (30, 26, 30, 28)
PAGE_SPACING = 6
PAGE_DESCRIPTION_GAP = 50
CARD_MARGINS = (16, 4, 16, 4)
CARD_ROW_SPACING = 0
CARD_RADIUS = 12
SETTING_ROW_MARGINS = (0, 11, 0, 11)
SETTING_ROW_SPACING = 18
SETTING_TEXT_SPACING = 3
SETTING_TEXT_MARGINS = (0, 0, 0, 0)
ROW_SEPARATOR_HEIGHT = 1
CONTROL_MIN_WIDTH = 150

SWITCH_SIZE = (42, 24)
SWITCH_TRACK_RADIUS = 11
SWITCH_THUMB_SIZE = 18
SWITCH_THUMB_X = {"off": 3, "on": 21}
SWITCH_INSET = 1
SWITCH_BORDER_WIDTH = 1
SWITCH_HOVER_LIGHTEN = 115
SWITCH_ANIMATION_MS = 150

DROPDOWN_MIN_SIZE = (150, 34)
DROPDOWN_VISIBLE_ITEMS = 6
DROPDOWN_MAX_HEIGHT = 252
DROPDOWN_ITEM_HEIGHT = 34
DROPDOWN_ITEM_SPACING = 2
DROPDOWN_RADIUS = 8
DROPDOWN_BORDER_INSET = (1, 1, -1, -1)
DROPDOWN_ICON_GAP = 30
DROPDOWN_TEXT_INSET = 11
DROPDOWN_ARROW_INSET = 16
DROPDOWN_ARROW_HALF_WIDTH = 4
DROPDOWN_ARROW_HALF_HEIGHT = 2
DROPDOWN_ARROW_STROKE = 1.6
DROPDOWN_BORDER_WIDTH = 1

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
}


def settings_stylesheet():
    p = PALETTE
    f = FONT
    return f"""
        QDialog {{ background: {p['background']}; color: {p['text']}; font-family: {FONT_FAMILY}; font-size: {f['dialog_size']}px; }}
        QStackedWidget#settingsPages {{ background: {p['background']}; }}
        QScrollArea#settingsPageScroll {{ background: {p['background']}; border: none; }}
        QWidget#settingsPage {{ background: {p['background']}; }}
        QListWidget#settingsSidebar {{ background: {p['surface']}; border: none; padding: {SIDEBAR_PADDING[0]}px {SIDEBAR_PADDING[1]}px; outline: none; }}
        QListWidget#settingsSidebar::item {{ background: transparent; border: none; padding: 0; margin: {NAV_ITEM_MARGINS[0]}px {NAV_ITEM_MARGINS[1]}px; }}
        QWidget#settingsNavRow {{ background: transparent; border-radius: {NAV_ROW_RADIUS}px; }}
        QLabel#settingsNavLabel {{ color: {p['text']}; font-weight: {f['sidebar_weight']}; }}
        QLabel#pageHeading {{ color: {p['text']}; font-size: {f['page_title_size']}px; font-weight: {f['page_title_weight']}; }}
        QLabel#pageSubtitle {{ color: {p['secondary_text']}; font-size: {f['page_subtitle_size']}px; font-weight: {f['page_subtitle_weight']}; padding-bottom: 2px; }}
        QFrame#settingsCard {{ background: {p['surface']}; border: 1px solid {p['border']}; border-radius: {CARD_RADIUS}px; }}
        QFrame#rowSeparator {{ background: {p['border']}; border: none; }}
        QPushButton#clearHistoryButton {{ color: #FF6961; background: {p['control_background']}; border: 1px solid {p['border']}; border-radius: 8px; padding: 8px 12px; font-size: {f['control_size']}px; font-weight: {f['control_weight']}; }}
        QPushButton#clearHistoryButton:hover {{ background: {p['control_hover_background']}; border-color: #FF6961; }}
        QPushButton#clearHistoryButton:pressed {{ background: {p['surface_hover']}; }}
        QLabel#settingTitle {{ color: {p['text']}; font-size: {f['setting_title_size']}px; font-weight: {f['setting_title_weight']}; }}
        QLabel#settingDescription {{ color: {p['secondary_text']}; font-size: {f['setting_description_size']}px; font-weight: {f['setting_description_weight']}; }}
        QCheckBox#settingsSwitch {{ background: transparent; border: none; }}
        QComboBox, QSpinBox, QDoubleSpinBox {{ color: {p['text']}; background: {p['control_background']}; border: 1px solid {p['control_border']}; border-radius: 8px; padding: 7px 10px; min-height: 18px; font-size: {f['control_size']}px; font-weight: {f['control_weight']}; selection-background-color: {p['accent']}; selection-color: {p['white']}; }}
        QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ color: {p['text']}; background: {p['control_hover_background']}; border-color: {p['control_hover_border']}; }}
        QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {p['control_focus_border']}; }}
        QComboBox#macCombo {{ padding: 0; border: none; background: transparent; min-height: {DROPDOWN_MIN_SIZE[1]}px; }}
        QLineEdit, QSpinBox QLineEdit, QDoubleSpinBox QLineEdit {{ color: {p['text']}; selection-background-color: {p['accent']}; selection-color: {p['white']}; font-weight: {f['control_weight']}; }}
        QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px; }}
        QScrollBar::handle:vertical {{ background: {p['border']}; min-height: 28px; border-radius: 4px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    """


def confirmation_stylesheet():
    p = PALETTE
    return f"""
        QMessageBox {{ background: {p['background']}; color: {p['text']}; font-family: {FONT_FAMILY}; font-size: {FONT['dialog_size']}px; }}
        QMessageBox QLabel {{ color: {p['text']}; font-family: {FONT_FAMILY}; font-size: {FONT['dialog_size']}px; }}
        QMessageBox QPushButton {{ color: {p['text']}; background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 7px; padding: 7px 14px; min-width: 76px; font-family: {FONT_FAMILY}; font-size: {FONT['dialog_size']}px; font-weight: 500; }}
        QMessageBox QPushButton:hover {{ background: {p['surface_hover']}; }}
        QMessageBox QPushButton:focus {{ border-color: {p['control_focus_border']}; outline: none; }}
        QMessageBox QPushButton#confirmClearButton {{ color: #FF6961; }}
    """


def dropdown_stylesheet():
    p = PALETTE
    return f"""
        QListView {{
            color: {p['text']};
            background: {p['control_background']};
            border: 1px solid {p['control_border']};
            border-radius: {DROPDOWN_RADIUS}px;
            outline: none;
            padding: 5px;
            font-size: {FONT['control_size']}px;
            font-weight: {FONT['control_weight']};
        }}
        QListView::item {{
            color: {p['text']};
            height: {DROPDOWN_ITEM_HEIGHT}px;
            padding: 0 10px;
            margin: 1px 2px;
            border-radius: 5px;
        }}
        QListView::item:hover, QListView::item:selected, QListView::item:focus {{
            color: {p['white']};
            background: {p['accent']};
        }}
        QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px; }}
        QScrollBar::handle:vertical {{ background: {p['border']}; min-height: 28px; border-radius: 4px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    """
