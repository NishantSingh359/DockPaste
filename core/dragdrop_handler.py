from pathlib import Path
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlparse

from PySide6.QtCore import QUrl

from core.image_store import ImageStore
from core.database import ClipboardDatabase, detect_type
from config import MAX_CLIP_ITEM_SIZE_BYTES
from utils.app_logging import log_exception
from utils.item_limits import is_oversized_image_file, is_oversized_text


IMAGE_FILE_SUFFIXES = {
    ".bmp", ".gif", ".heic", ".heif", ".jpeg", ".jpg", ".png",
    ".tif", ".tiff", ".webp", ".avif",
}
WEB_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)



class DragDropHandler:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.image_store = ImageStore(self.base_dir)
        self.enforce_size_limit = True
        self.db = ClipboardDatabase(self.base_dir)
        self.oversized_item_rejected = False

    def set_size_limit_enabled(self, enabled):
        self.enforce_size_limit = bool(enabled)
        self.image_store.set_size_limit_enabled(enabled)


    def can_accept(self, mime_data):
        try:
            return (
                mime_data.hasUrls()
                or mime_data.hasImage()
                or mime_data.hasText()
                or mime_data.hasHtml()
                or self._image_source_url(mime_data) is not None
            )
        except Exception:
            log_exception("Failed to inspect drag data")
            return False

    def extract_items(self, mime_data):
        items = []
        self.oversized_item_rejected = False

        try:
            has_image_payload = mime_data.hasImage()
            # Browser drag MIME differs by engine: some provide a bitmap,
            # others only a URL or HTML fragment. Inspect every payload so
            # image drags consistently resolve to their web source when present.
            image_source_url = self._image_source_url(mime_data)
            if mime_data.hasUrls():
                url_items = self._extract_urls(mime_data.urls())
                accepted_url_items = []

                # store file/folder paths into DB as type='path'
                for it in url_items:
                    # keep only filesystem paths
                    p = Path(it)
                    if p.exists() and (p.is_file() or p.is_dir()):
                        is_local_image = p.is_file() and p.suffix.lower() in IMAGE_FILE_SUFFIXES
                        if is_local_image:
                            # A browser may expose an image cache alias and the
                            # actual source URL in the same drag. The URL is the
                            # useful, stable representation of that web image.
                            if image_source_url:
                                continue
                            # If there is no source URL, use the decoded payload
                            # below instead of saving a potentially reused name
                            # like images-1.jpg as the clip identity.
                            if has_image_payload:
                                continue
                        if self.enforce_size_limit and is_oversized_image_file(p):
                            self.oversized_item_rejected = True
                            continue
                        self._store_item(it, "path")
                    elif self.enforce_size_limit and is_oversized_text(it):
                        self.oversized_item_rejected = True
                        continue
                    elif it.lower().startswith(("http://", "https://", "ftp://")):
                        self._store_item(it, "link")
                    else:
                        # Ignore unsupported external schemes instead of
                        # presenting them as clipboard text.
                        continue
                    accepted_url_items.append(it)
                items.extend(accepted_url_items)

            if image_source_url and image_source_url not in items:
                self._store_item(image_source_url, "link")
                items.append(image_source_url)

            # For a web image drag, retain the image's URL and ignore the
            # parallel bitmap. Copy Image is handled by clipboard monitoring.
            # For a local browser cache alias without a source URL, retain the
            # actual bitmap so repeated generic filenames do not collide.
            if has_image_payload and not image_source_url:
                image_data = mime_data.imageData()
                source_size_bytes = self.image_store.image_payload_size(image_data, mime_data)
                if (self.enforce_size_limit and source_size_bytes is not None
                        and source_size_bytes > MAX_CLIP_ITEM_SIZE_BYTES):
                    self.oversized_item_rejected = True
                    image_path = None
                else:
                    image_path = self._save_image(image_data, source_size_bytes)
                    image_file = Path(image_path) if image_path else None
                    if (self.enforce_size_limit and image_file and image_file.is_file()
                            and image_file.stat().st_size > MAX_CLIP_ITEM_SIZE_BYTES):
                        image_file.unlink(missing_ok=True)
                        self.oversized_item_rejected = True
                        image_path = None
                if image_path:
                    self._store_item(image_path, "img")
                    items.append(image_path)

            if not items and not self.oversized_item_rejected and mime_data.hasText():
                raw_text = mime_data.text()
                if not self.enforce_size_limit or not is_oversized_text(raw_text):
                    text = raw_text.strip()
                    if text:
                        item_type = detect_type(text)
                        if item_type == "text" and text.lower().startswith(("http://", "https://", "ftp://")):
                            item_type = "link"
                        self._store_item(text, item_type)
                        items.append(text)
                else:
                    self.oversized_item_rejected = True

            if not items and not self.oversized_item_rejected and mime_data.hasHtml():
                raw_html = mime_data.html()
                if not self.enforce_size_limit or not is_oversized_text(raw_html):
                    html = raw_html.strip()
                    if html:
                        items.append(html)
                else:
                    self.oversized_item_rejected = True
        except Exception:
            log_exception("Failed to extract drag/drop items")
            return []

        return self._unique(items)

    def _image_source_url(self, mime_data):
        """Find the image's web URL across common browser MIME formats."""
        if mime_data.hasUrls():
            for url in mime_data.urls():
                if not url.isLocalFile() and url.scheme().lower() in ("http", "https"):
                    return url.toString()

        if mime_data.hasText():
            text_url = self._first_web_url(mime_data.text())
            if text_url:
                return text_url

        if mime_data.hasHtml():
            source = self._image_url_from_html(mime_data.html())
            if source:
                return source

        # Firefox based browsers can publish the source only as
        # text/x-moz-url; Windows browsers may use UniformResourceLocatorW.
        # QMimeData.hasUrls() does not expose every vendor-specific format as
        # QUrl, so inspect URL, URI, and HTML text formats directly as a
        # fallback. Strip NULs to support UTF-16 Windows payloads.
        try:
            for mime_type in mime_data.formats():
                name = str(mime_type).lower()
                if not any(token in name for token in ("url", "uri", "locator", "html")):
                    continue
                raw = bytes(mime_data.data(mime_type))
                if not raw:
                    continue
                decoded = []
                for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
                    try:
                        value = raw.decode(encoding).replace("\x00", "").strip()
                    except (UnicodeDecodeError, LookupError):
                        continue
                    if value and value not in decoded:
                        decoded.append(value)

                for value in decoded:
                    if "html" in name:
                        source = self._image_url_from_html(value)
                        if source:
                            return source
                    source = self._first_web_url(value)
                    if source:
                        return source
        except Exception:
            log_exception("Failed to inspect browser-specific drag URL formats")
        return None

    @staticmethod
    def _first_web_url(value):
        match = WEB_URL_PATTERN.search(value or "")
        if not match:
            return None
        candidate = match.group(0).rstrip(".,;:!?)]}")
        parsed = urlparse(candidate)
        if parsed.scheme.lower() in ("http", "https") and parsed.netloc:
            return candidate
        return None

    @staticmethod
    def _image_url_from_html(html):
        parser = _ImageSourceParser()
        try:
            parser.feed(html)
        except Exception:
            log_exception("Failed to inspect dragged image HTML")
            return None
        base_url = parser.base_url
        for source in parser.sources:
            resolved = urljoin(base_url, source) if base_url else source
            parsed = urlparse(resolved)
            if parsed.scheme.lower() in ("http", "https") and parsed.netloc:
                return resolved
        return None

    def _extract_urls(self, urls):
        items = []
        for url in urls:
            if url.isLocalFile():
                items.append(url.toLocalFile())
            else:
                items.append(url.toString())

        return items

    def _save_image(self, image_data, source_size_bytes=None):
        return self.image_store.save_image(image_data, "drop", source_size_bytes)

    def _store_item(self, content, item_type):
        try:
            self.db.insert_with_type(content, item_type)
        except Exception:
            log_exception("Failed to store dragged clipboard item")

    def _unique(self, items):
        seen = set()
        result = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result


class _ImageSourceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []
        self.base_url = None

    def handle_starttag(self, tag, attrs):
        attributes = {name.lower(): value for name, value in attrs if value}
        if tag.lower() == "base" and attributes.get("href"):
            self.base_url = attributes["href"]
            return
        if tag.lower() != "img":
            return
        source = attributes.get("src")
        if source:
            self.sources.append(source)
