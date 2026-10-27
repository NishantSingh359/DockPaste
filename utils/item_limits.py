from pathlib import Path

from config import MAX_CLIP_ITEM_SIZE_BYTES

IMAGE_FILE_SUFFIXES = {
    ".avif", ".bmp", ".gif", ".heic", ".heif", ".jfif", ".jpe",
    ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp",
}


def is_oversized_image_file(path):
    """Apply the clipboard size limit to image files stored as paths."""
    try:
        candidate = Path(path)
        return (
            candidate.is_file()
            and candidate.suffix.casefold() in IMAGE_FILE_SUFFIXES
            and candidate.stat().st_size > MAX_CLIP_ITEM_SIZE_BYTES
        )
    except OSError:
        return False


def is_oversized_text(text):
    return len(str(text).encode("utf-8")) > MAX_CLIP_ITEM_SIZE_BYTES
