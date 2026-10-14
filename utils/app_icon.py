"""Shared multi-resolution application icon helpers."""

import sys
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon


ICON_SIZES = (16, 24, 32, 48, 56, 256)


def _asset_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def app_icon_path(size=256):
    return _asset_root() / "assets" / "app_icons" / f"icon{size}x{size}.ico"


def create_app_icon():
    """Build a QIcon containing the best supplied bitmap for each UI size."""
    icon = QIcon()
    for size in ICON_SIZES:
        path = app_icon_path(size)
        if path.is_file():
            icon.addFile(str(path), QSize(size, size))
    return icon
