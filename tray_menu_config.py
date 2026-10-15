"""Appearance for DockPaste's system-tray menu, independent of shelf themes."""

from PySide6.QtCore import QByteArray, QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QProxyStyle, QStyle


PALETTE = {
    "background": "#232323",
    "border": "#333333",
    "text": "#d2d2d2",
    "accent": "#0A84FF",
    "selected_text": "#d2d2d2",
    "separator": "#333333",
}

MENU_WIDTH = 120
MENU_ICON_SIZE = 22
MENU_ICON_STROKE_WIDTH = 2.2
MENU_RADIUS = 10
MENU_BORDER_WIDTH = 1
MENU_FONT_FAMILY = "Inter, 'Segoe UI', sans-serif"
MENU_FONT_SIZE = 15
MENU_FONT_WEIGHT = 600
MENU_PADDING = (2, 2)
ITEM_PADDING = (4, 4)
ITEM_CONTENT_LEFT_PADDING = 6
ITEM_MARGIN = (3, 3)
ITEM_RADIUS = 7
ITEM_MIN_WIDTH = 64
SEPARATOR_HEIGHT = 1
SEPARATOR_MARGINS = (4, 8)

_ICON_PATHS = {
    "settings": (
        '<circle cx="12" cy="12" r="7.5"/>'
        '<circle cx="12" cy="12" r="2.5"/>'
        '<path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22"/>'
        '<path d="m4.93 4.93 1.77 1.77m10.6 10.6 1.77 1.77m0-14.14L17.3 6.7M6.7 17.3l-1.77 1.77"/>'
    ),
    "exit": (
        '<path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4"/>'
        '<path d="M14 8l4 4-4 4M18 12H9"/>'
    ),
}


def create_icon(name, color=None):
    """Render a crisp 2x line icon for a tray-menu action."""
    color = color or PALETTE["accent"]
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="{MENU_ICON_STROKE_WIDTH}" stroke-linecap="round" stroke-linejoin="round">'
        + _ICON_PATHS[name]
        + '</svg>'
    )
    pixmap = QPixmap(MENU_ICON_SIZE * 2, MENU_ICON_SIZE * 2)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    inset = ITEM_CONTENT_LEFT_PADDING * 2
    glyph_size = MENU_ICON_SIZE - ITEM_CONTENT_LEFT_PADDING
    icon_extent = glyph_size * 2
    vertical_inset = (MENU_ICON_SIZE - glyph_size) * 1
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(
        painter,
        QRectF(inset, vertical_inset, icon_extent, icon_extent),
    )
    painter.end()
    pixmap.setDevicePixelRatio(2.0)
    return QIcon(pixmap)


class TrayMenuStyle(QProxyStyle):
    """Give the popup a predictable, configurable icon size on Windows."""

    def pixelMetric(self, metric, option=None, widget=None):
        if metric == QStyle.PixelMetric.PM_SmallIconSize:
            return MENU_ICON_SIZE
        return super().pixelMetric(metric, option, widget)


class _MenuIconStateResetter(QObject):
    """Clear hover-only icon tint when the pointer or activation leaves the menu."""

    def __init__(self, reset_icons, parent):
        super().__init__(parent)
        self._reset_icons = reset_icons

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Leave, QEvent.Type.WindowDeactivate):
            self._reset_icons(None)
        return False


def menu_stylesheet():
    p = PALETTE
    return f"""
        QMenu {{
            color: {p['text']};
            background: {p['background']};
            border: {MENU_BORDER_WIDTH}px solid {p['border']};
            border-radius: {MENU_RADIUS}px;
            padding: {MENU_PADDING[0]}px {MENU_PADDING[1]}px;
            font-family: {MENU_FONT_FAMILY};
            font-size: {MENU_FONT_SIZE}px;
            font-weight: {MENU_FONT_WEIGHT};
        }}
        QMenu::item {{
            color: {p['text']};
            background: transparent;
            padding: {ITEM_PADDING[0]}px {ITEM_PADDING[1]}px {ITEM_PADDING[0]}px {ITEM_CONTENT_LEFT_PADDING}px;
            margin: {ITEM_MARGIN[0]}px {ITEM_MARGIN[1]}px;
            border-radius: {ITEM_RADIUS}px;
            min-width: {ITEM_MIN_WIDTH}px;
        }}
        QMenu::item:selected {{
            color: {p['selected_text']};
            background: {p['accent']};
        }}
        QMenu::separator {{
            height: {SEPARATOR_HEIGHT}px;
            background: {p['separator']};
            margin: {SEPARATOR_MARGINS[0]}px {SEPARATOR_MARGINS[1]}px;
        }}
    """


def style_menu(menu, actions):
    """Apply the shared appearance and blue/white hover icon states."""
    menu_style = TrayMenuStyle("Fusion")
    menu_style.setParent(menu)
    menu.setStyle(menu_style)
    menu._tray_menu_style = menu_style
    menu.setStyleSheet(menu_stylesheet())
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    menu.setFixedWidth(MENU_WIDTH)
    icons = {
        action: (
            create_icon(name),
            create_icon(name, PALETTE["selected_text"]),
        )
        for action, name in actions.items()
    }
    for action, (normal, _) in icons.items():
        action.setIcon(normal)

    def set_hovered_icon(hovered_action):
        for action, (normal, active) in icons.items():
            action.setIcon(active if action is hovered_action else normal)

    menu.hovered.connect(set_hovered_icon)
    menu.aboutToHide.connect(lambda: set_hovered_icon(None))
    icon_state_resetter = _MenuIconStateResetter(set_hovered_icon, menu)
    menu.installEventFilter(icon_state_resetter)
    menu._tray_menu_icon_state_resetter = icon_state_resetter
