from pathlib import Path

from config import MAX_CLIP_ITEM_SIZE_BYTES


def is_oversized_file(path):
    """Check a file against the clipboard limit; folders are stored as paths."""
    try:
        candidate = Path(path)
        if candidate.is_file():
            return candidate.stat().st_size > MAX_CLIP_ITEM_SIZE_BYTES
        return False
    except OSError:
        return False


def is_oversized_text(text):
    return len(str(text).encode("utf-8")) > MAX_CLIP_ITEM_SIZE_BYTES
