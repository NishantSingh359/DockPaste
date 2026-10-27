import base64
import ctypes
import http.client
import ipaddress
import json
import os
import socket
from html.parser import HTMLParser
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from threading import Lock
from time import monotonic
from urllib.parse import parse_qs, urlsplit
from urllib.request import (
    HTTPHandler,
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

from PySide6.QtCore import QObject, QByteArray, QBuffer, QMimeData, Qt, Signal, Slot
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPixmap, QClipboard

from core.image_store import ImageStore
from core.database import ClipboardDatabase
from config import MAX_CLIP_ITEM_SIZE_BYTES
from utils.app_logging import get_logger, log_exception, safe_slot
from utils.item_limits import is_oversized_image_file, is_oversized_text

PASTE_IMAGE_CACHE_MAX_BYTES = 48 * 1024 * 1024
MAX_PERSISTED_RICH_FORMAT_BYTES = 16 * 1024 * 1024
MAX_CLIPBOARD_RESTORE_BYTES = 64 * 1024 * 1024


def _resolve_public_http_url(url):
    """Resolve a copied image URL and reject non-public network destinations."""
    parsed = urlsplit(url)
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only public HTTP(S) image URLs are allowed")

    try:
        port = parsed.port or (443 if scheme == "https" else 80)
    except ValueError as exc:
        raise ValueError("Invalid image URL port") from exc
    if port not in {80, 443}:
        raise ValueError("Non-standard image URL ports are not allowed")

    addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise ValueError("Image URL host did not resolve")

    resolved = []
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("Image URL resolves to a non-public address")
        if ip.compressed not in resolved:
            resolved.append(ip.compressed)
    return parsed, port, resolved[0]


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """Connect to the already validated address to prevent DNS rebinding."""

    def __init__(self, host, address, **kwargs):
        super().__init__(host, **kwargs)
        self._pinned_address = address

    def connect(self):
        self.sock = socket.create_connection(
            (self._pinned_address, self.port), self.timeout, self.source_address
        )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection pinned to a validated IP, retaining hostname checks."""

    def __init__(self, host, address, **kwargs):
        super().__init__(host, **kwargs)
        self._pinned_address = address

    def connect(self):
        sock = socket.create_connection(
            (self._pinned_address, self.port), self.timeout, self.source_address
        )
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


class _PublicHTTPHandler(HTTPHandler):
    def http_open(self, request):
        _, _, address = _resolve_public_http_url(request.full_url)
        return self.do_open(
            lambda host, **kwargs: _PinnedHTTPConnection(host, address, **kwargs),
            request,
        )


class _PublicHTTPSHandler(HTTPSHandler):
    def https_open(self, request):
        _, _, address = _resolve_public_http_url(request.full_url)
        return self.do_open(
            lambda host, **kwargs: _PinnedHTTPSConnection(host, address, **kwargs),
            request,
            context=self._context,
            check_hostname=self._check_hostname,
        )


class _PublicRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        _resolve_public_http_url(new_url)
        return super().redirect_request(
            request, file_pointer, code, message, headers, new_url
        )


class ClipboardManager(QObject):
    text_copied = Signal(str)
    image_copied = Signal(str)
    path_copied = Signal(str)
    oversized_item_rejected = Signal()

    def __init__(self, base_dir):
        super().__init__()
        self.clipboard = QApplication.clipboard()
        self.image_store = ImageStore(base_dir)
        self.enforce_size_limit = True
        self.db = ClipboardDatabase(base_dir)
        self._migrate_legacy_image_names()
        self._last_text = ""
        self._last_image_cache_key = None
        self._last_image_hash = None
        self._last_notified_clipboard_sequence = None
        self._clipboard_image_epoch = 0
        self._internal_clipboard_sequences = set()
        self._internal_clipboard_write = False
        self._internal_clipboard_signal_seen = False
        self._pending_image_hashes = set()
        self._pending_image_updates = {}
        self._ignored_image_hashes = {}
        self._ignored_image_fingerprints = []
        self._ignore_snipping_tool_until = 0.0
        self._paste_image_cache = OrderedDict()
        self._paste_image_cache_bytes = 0
        self._ignore_next_count = 0
        self._pending_restore = False
        self._restore_text = None
        self._restore_image = None
        self._restore_image_hash = None
        self._clipboard_image_snapshot = None
        self._clipboard_image_snapshot_hash = None
        self._clipboard_rich_formats_snapshot = {}
        self._restore_rich_formats = {}
        self._restore_clipboard_formats = None
        self._rich_formats_by_image_path = {}
        self._image_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="copypin-image")
        self._image_lock = Lock()
        self._reserved_image_records = {}
        self._reserved_image_records_lock = Lock()
        self.clipboard.dataChanged.connect(self.on_data_changed)

    def _migrate_legacy_image_names(self):
        """Rename stored screenshot paths and files to the current img-N scheme."""
        try:
            records = []
            offset = 0
            page_size = 500
            while True:
                page = self.db.get_by_type("img", limit=page_size, offset=offset)
                records.extend(page)
                if len(page) < page_size:
                    break
                offset += page_size

            managed_dir = self.image_store.thumbnail_dir.resolve()
            legacy_records = []
            for record in records:
                old_path = Path(record["content"])
                if (
                    old_path.parent.resolve() == managed_dir
                    and old_path.name.lower().startswith("screenshot-")
                    and old_path.suffix.lower() == ".png"
                    and old_path.stem[len("screenshot-"):].isdigit()
                ):
                    legacy_records.append((record, old_path))

            occupied_names = {
                Path(record["content"]).name.casefold()
                for record in records
                if Path(record["content"]).name.lower().startswith("img-")
            }
            occupied_names.update(path.name.casefold() for path in managed_dir.glob("img-*.png"))

            next_number = 1
            for record, old_path in reversed(legacy_records):
                while f"img-{next_number}.png".casefold() in occupied_names:
                    next_number += 1
                new_path = managed_dir / f"img-{next_number}.png"
                old_sidecar = Path(f"{old_path}.mime.json")
                new_sidecar = Path(f"{new_path}.mime.json")
                renamed_file = False
                renamed_sidecar = False
                try:
                    if old_path.exists():
                        old_path.rename(new_path)
                        renamed_file = True
                    if old_sidecar.exists():
                        old_sidecar.rename(new_sidecar)
                        renamed_sidecar = True
                    if not self.db.update_content(record["id"], str(new_path)):
                        raise RuntimeError(f"Clipboard image record {record['id']} disappeared")
                except Exception:
                    if renamed_sidecar and new_sidecar.exists():
                        new_sidecar.rename(old_sidecar)
                    if renamed_file and new_path.exists():
                        new_path.rename(old_path)
                    raise
                occupied_names.add(new_path.name.casefold())
                next_number += 1
        except Exception:
            log_exception("Failed to migrate legacy screenshot names")

    def get_db(self):
        """Return the database instance for external queries."""
        return self.db

    def set_size_limit_enabled(self, enabled):
        self.enforce_size_limit = bool(enabled)
        self.image_store.set_size_limit_enabled(enabled)

    def ignore_image_capture(self, image_path):
        """Ignore clipboard copies of an image opened by an external viewer.

        Register exact and perceptual identities before launching the viewer.
        Snipping Tool can publish the same image after re-encoding or resizing it.
        """
        self._ignore_snipping_tool_until = monotonic() + 60
        try:
            image = QImage(str(image_path))
            fingerprint = self._image_fingerprint(image)
            if fingerprint:
                self._ignored_image_fingerprints.append(
                    (*fingerprint, self._ignore_snipping_tool_until)
                )
        except Exception:
            log_exception("Failed to fingerprint image opened in external viewer")
        self._image_executor.submit(self._register_ignored_image, str(image_path))

    @staticmethod
    def _image_fingerprint(image):
        if image is None or image.isNull():
            return None
        sample = image.scaled(8, 8, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        luminance = [
            (
                11 * ((sample.pixel(x, y) >> 16) & 0xFF)
                + 16 * ((sample.pixel(x, y) >> 8) & 0xFF)
                + 5 * (sample.pixel(x, y) & 0xFF)
            ) // 32
            for y in range(8)
            for x in range(8)
        ]
        average = sum(luminance) / len(luminance)
        fingerprint = sum(1 << index for index, value in enumerate(luminance) if value >= average)
        aspect_ratio = image.width() / max(1, image.height())
        return fingerprint, aspect_ratio

    def _matches_ignored_image_fingerprint(self, image):
        candidate = self._image_fingerprint(image)
        if candidate is None:
            return False
        fingerprint, aspect_ratio = candidate
        now = monotonic()
        self._ignored_image_fingerprints = [
            item for item in self._ignored_image_fingerprints if item[2] >= now
        ]
        for known_fingerprint, known_ratio, _ in self._ignored_image_fingerprints:
            ratio_delta = abs(aspect_ratio - known_ratio) / max(known_ratio, 0.01)
            bit_delta = (fingerprint ^ known_fingerprint).bit_count()
            if ratio_delta <= 0.12 and bit_delta <= 10:
                return True
        return False

    @staticmethod
    def _clipboard_owner_is_snipping_tool():
        """Return whether Snipping Tool currently owns the Windows clipboard."""
        if os.name != "nt":
            return False

        process_handle = None
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            user32.GetClipboardOwner.restype = ctypes.c_void_p
            user32.GetWindowThreadProcessId.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_ulong),
            ]
            user32.GetWindowThreadProcessId.restype = ctypes.c_ulong
            kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
            kernel32.OpenProcess.restype = ctypes.c_void_p
            kernel32.QueryFullProcessImageNameW.argtypes = [
                ctypes.c_void_p,
                ctypes.c_ulong,
                ctypes.c_wchar_p,
                ctypes.POINTER(ctypes.c_ulong),
            ]
            kernel32.QueryFullProcessImageNameW.restype = ctypes.c_int
            kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel32.CloseHandle.restype = ctypes.c_int
            owner_window = user32.GetClipboardOwner()
            if not owner_window:
                return False

            process_id = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(owner_window, ctypes.byref(process_id))
            if not process_id.value:
                return False

            process_handle = kernel32.OpenProcess(0x1000, False, process_id.value)
            if not process_handle:
                return False

            executable_path = ctypes.create_unicode_buffer(32768)
            path_length = ctypes.c_ulong(len(executable_path))
            if not kernel32.QueryFullProcessImageNameW(
                process_handle, 0, executable_path, ctypes.byref(path_length)
            ):
                return False

            process_name = os.path.basename(executable_path.value).casefold()
            return process_name in {"snippingtool.exe", "screenclippinghost.exe"}
        except (AttributeError, OSError, TypeError, ValueError):
            return False
        finally:
            if process_handle:
                try:
                    ctypes.windll.kernel32.CloseHandle(process_handle)
                except (AttributeError, OSError):
                    pass

    @classmethod
    def _snipping_tool_is_active_or_clipboard_owner(cls):
        if cls._clipboard_owner_is_snipping_tool():
            return True
        if os.name != "nt":
            return False
        try:
            user32 = ctypes.windll.user32
            user32.GetForegroundWindow.restype = ctypes.c_void_p
            user32.GetWindowTextW.argtypes = [
                ctypes.c_void_p,
                ctypes.c_wchar_p,
                ctypes.c_int,
            ]
            user32.GetWindowTextW.restype = ctypes.c_int
            window = user32.GetForegroundWindow()
            if not window:
                return False
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(window, title, len(title))
            return "snipping tool" in title.value.casefold()
        except (AttributeError, OSError, TypeError, ValueError):
            return False

    def _register_ignored_image(self, image_path):
        try:
            image = QImage(image_path)
            image_hash = self._hash_image(image) if not image.isNull() else None
            if image_hash:
                expires_at = monotonic() + 60
                self._ignored_image_hashes = {
                    known_hash: expiry
                    for known_hash, expiry in self._ignored_image_hashes.items()
                    if expiry >= monotonic()
                }
                self._ignored_image_hashes[image_hash] = expires_at
        except Exception:
            log_exception("Failed to register image opened in external viewer")

    def set_text_for_paste(self, text, temporary=False):
        if temporary and not self._pending_restore:
            snapshot = self._snapshot_clipboard()
            if snapshot is None:
                return False
            self._store_restore_snapshot(snapshot)
        elif not temporary:
            self._pending_restore = False
            self._restore_clipboard_formats = None

        self._last_text = text
        self._write_clipboard(
            lambda: self.clipboard.setText(text, QClipboard.Clipboard)
        )
        self._clipboard_image_snapshot = None
        self._clipboard_image_snapshot_hash = None
        self._clipboard_rich_formats_snapshot = {}
        if temporary:
            self._pending_restore = True
        return True

    def _snapshot_clipboard(self):
        """Copy the current clipboard MIME payload before a temporary paste."""
        try:
            mime = self.clipboard.mimeData(QClipboard.Clipboard)
            if mime is None:
                return {"formats": {}, "image": None, "text": None}

            formats = {}
            total_bytes = 0
            for raw_format in mime.formats():
                format_name = str(raw_format)
                payload = bytes(mime.data(raw_format))
                total_bytes += len(payload)
                if total_bytes > MAX_CLIPBOARD_RESTORE_BYTES:
                    return None
                formats[format_name] = payload

            image = None
            if mime.hasImage():
                image_data = mime.imageData()
                if isinstance(image_data, QPixmap):
                    image = image_data.toImage()
                elif isinstance(image_data, QImage) and not image_data.isNull():
                    image = QImage(image_data)

            return {
                "formats": formats,
                "image": image,
                "text": mime.text() if mime.hasText() else None,
            }
        except Exception:
            log_exception("Failed to snapshot clipboard before paste")
            return None

    def _store_restore_snapshot(self, snapshot):
        self._restore_clipboard_formats = snapshot["formats"]
        self._restore_text = snapshot["text"]
        self._restore_image = snapshot["image"]
        self._restore_image_hash = None
        self._restore_rich_formats = {
            name: payload
            for name, payload in snapshot["formats"].items()
            if name.casefold() != "application/x-qt-image"
        }

    def set_image_for_paste(self, image_path, temporary=False):
        try:
            image, image_hash = self._load_paste_image(image_path)
            if image.isNull():
                return False

            if temporary and not self._pending_restore:
                snapshot = self._snapshot_clipboard()
                if snapshot is None:
                    return False
                self._store_restore_snapshot(snapshot)
            elif not temporary:
                self._pending_restore = False
                self._restore_clipboard_formats = None

            self._last_image_cache_key = image.cacheKey()
            self._last_image_hash = image_hash
            rich_formats = self._load_rich_formats(image_path)
            if rich_formats:
                mime_data = self._mime_data_with_image(rich_formats, image)
                self._write_clipboard(
                    lambda: self.clipboard.setMimeData(mime_data)
                )
            else:
                self._write_clipboard(
                    lambda: self.clipboard.setImage(image, QClipboard.Clipboard)
                )
            self._clipboard_image_snapshot = image
            self._clipboard_image_snapshot_hash = image_hash
            self._clipboard_rich_formats_snapshot = rich_formats or {}
            if temporary:
                self._pending_restore = True
            return True
        except Exception:
            log_exception("Failed to set image for paste")
            return False

    def restore_previous_clipboard(self):
        if not getattr(self, "_pending_restore", False):
            return

        self._pending_restore = False
        previous_text = getattr(self, "_restore_text", None)
        previous_image = getattr(self, "_restore_image", None)
        previous_formats = self._restore_clipboard_formats
        if previous_formats is not None:
            if not previous_formats and previous_image is None:
                self._write_clipboard(
                    lambda: self.clipboard.clear(QClipboard.Clipboard)
                )
            else:
                mime_data = QMimeData()
                if previous_image is not None:
                    mime_data.setImageData(previous_image)
                for format_name, payload in previous_formats.items():
                    if format_name.casefold() == "application/x-qt-image":
                        continue
                    mime_data.setData(format_name, QByteArray(payload))
                self._write_clipboard(
                    lambda: self.clipboard.setMimeData(
                        mime_data, QClipboard.Clipboard
                    )
                )
            self._last_text = previous_text or ""
            self._clipboard_image_snapshot = previous_image
            self._clipboard_image_snapshot_hash = (
                self._restore_image_hash or self._hash_image(previous_image)
                if previous_image is not None
                else None
            )
            self._last_image_hash = self._clipboard_image_snapshot_hash
            self._clipboard_rich_formats_snapshot = (
                dict(self._restore_rich_formats) if previous_image is not None else {}
            )
            self._last_image_cache_key = (
                previous_image.cacheKey() if previous_image is not None else None
            )
            self._restore_clipboard_formats = None
            return
        if previous_image is not None:
            self._last_image_cache_key = previous_image.cacheKey()
            self._last_image_hash = (
                self._restore_image_hash or self._hash_image(previous_image)
            )
            if self._restore_rich_formats:
                mime_data = self._mime_data_with_image(
                    self._restore_rich_formats, previous_image
                )
                self._write_clipboard(
                    lambda: self.clipboard.setMimeData(mime_data)
                )
            else:
                self._write_clipboard(
                    lambda: self.clipboard.setImage(
                        previous_image, QClipboard.Clipboard
                    )
                )
            self._clipboard_image_snapshot = previous_image
            self._clipboard_image_snapshot_hash = self._last_image_hash
            self._clipboard_rich_formats_snapshot = self._restore_rich_formats or {}
            return
        if previous_text is not None:
            self._last_text = previous_text
            self._write_clipboard(
                lambda: self.clipboard.setText(previous_text, QClipboard.Clipboard)
            )
            self._clipboard_image_snapshot = None
            self._clipboard_image_snapshot_hash = None
            self._clipboard_rich_formats_snapshot = {}
            return

        self._last_text = ""
        self._last_image_cache_key = None
        self._last_image_hash = None
        self._clipboard_image_snapshot = None
        self._clipboard_image_snapshot_hash = None
        self._clipboard_rich_formats_snapshot = {}
        self._write_clipboard(
            lambda: self.clipboard.clear(QClipboard.Clipboard)
        )

    def _write_clipboard(self, write_operation):
        """Mark app-owned clipboard writes so delayed signals cannot hide new copies."""
        self._internal_clipboard_write = True
        self._internal_clipboard_signal_seen = False
        try:
            write_operation()
        finally:
            self._internal_clipboard_write = False
            sequence = self._windows_clipboard_sequence_number()
            if sequence is None:
                if not self._internal_clipboard_signal_seen:
                    self._ignore_next_count += 1
            elif not self._internal_clipboard_signal_seen:
                self._internal_clipboard_sequences.add(sequence)
                if len(self._internal_clipboard_sequences) > 32:
                    self._internal_clipboard_sequences = {
                        sequence
                    }

    @Slot()
    @safe_slot("Failed to process clipboard change")
    def on_data_changed(self):
        if self._internal_clipboard_write:
            self._internal_clipboard_signal_seen = True
            return

        # Process each distinct Windows clipboard sequence. Debouncing here can
        # lose two genuine copies made close together because the clipboard only
        # retains the newest payload by the time the timer fires.
        if self.sender() is self.clipboard:
            sequence = self._windows_clipboard_sequence_number()
            if sequence is not None:
                if sequence in self._internal_clipboard_sequences:
                    self._internal_clipboard_sequences.discard(sequence)
                    return
                if sequence == self._last_notified_clipboard_sequence:
                    return
                self._last_notified_clipboard_sequence = sequence
            elif getattr(self, "_ignore_next_count", 0) > 0:
                self._ignore_next_count -= 1
                return
            self._process_clipboard_change()
            return

        if getattr(self, "_ignore_next_count", 0) > 0:
            self._ignore_next_count -= 1
            return

        # Keep direct calls useful for integrations and unit-level callers.
        self._process_clipboard_change()

    @safe_slot("Failed to process clipboard change")
    def _process_clipboard_change(self):
        sequence = self._windows_clipboard_sequence_number()
        mime = self.clipboard.mimeData()
        html_link = self._single_copied_html_link(mime)
        has_image_payload = mime.hasImage()
        image_url = (
            None if has_image_payload else self._clipboard_image_source_url(mime)
        )
        if not has_image_payload and not image_url:
            # Consecutive image notifications can be duplicate representations
            # of one capture. A non-image clipboard item breaks that run, so a
            # later intentional recopy of the same image remains a new copy.
            self._clipboard_image_epoch += 1
        # Prefer actual clipboard image data over its source URL. Some browsers
        # expose only the source URL, handled by the remote image path below.
        if has_image_payload:
            owner_name = self._windows_clipboard_owner_name()
            formats = tuple(
                name.decode("utf-8", errors="replace") if isinstance(name, bytes) else str(name)
                for name in mime.formats()
            )
            image = self.clipboard.image()
            if image.isNull():
                self._clipboard_image_snapshot = None
                self._clipboard_image_snapshot_hash = None
                self._clipboard_rich_formats_snapshot = {}
                if image_url:
                    self._queue_remote_image(image_url)
                    return
                return
            self._clipboard_image_snapshot = image
            self._clipboard_image_snapshot_hash = None

            if self._matches_ignored_image_fingerprint(image):
                self._last_image_cache_key = image.cacheKey()
                return

            if (
                monotonic() <= self._ignore_snipping_tool_until
                and self._snipping_tool_is_active_or_clipboard_owner()
            ):
                self._last_image_cache_key = image.cacheKey()
                return

            cache_key = image.cacheKey()
            if cache_key == self._last_image_cache_key:
                return

            # Read an already-encoded image payload when available. Do not use
            # decoded pixel memory as a proxy for file size; providers that only
            # expose QImage data are measured by PNG encoding in the worker.
            source_size_bytes = self.image_store.encoded_mime_payload_size(mime)
            if (
                self.enforce_size_limit
                and source_size_bytes is not None
                and source_size_bytes > MAX_CLIP_ITEM_SIZE_BYTES
            ):
                # Remember this image so repeated clipboard notifications do not
                # repeatedly inspect and reject the same oversized content.
                self._last_image_cache_key = cache_key
                if self.enforce_size_limit:
                    self.oversized_item_rejected.emit()
                return

            # Only copy rich format payloads after deduplication and size checks.
            # Some applications publish large native clipboard formats, and
            # reading them eagerly would add work to every clipboard update.
            rich_formats = self._capture_rich_formats(mime)
            self._clipboard_rich_formats_snapshot = rich_formats

            self._last_image_cache_key = cache_key
            reserved_path = self._reserve_image_record()
            if reserved_path is None:
                self._last_image_cache_key = cache_key
                return
            self._image_executor.submit(
                self._process_image,
                image,
                None,
                False,
                source_size_bytes,
                rich_formats,
                (sequence, owner_name, formats, self._clipboard_image_epoch),
                reserved_path,
            )
            return

        if image_url:
            self._queue_remote_image(image_url)
            return

        if mime.hasUrls():
            self._clipboard_image_snapshot = None
            self._clipboard_image_snapshot_hash = None
            self._clipboard_rich_formats_snapshot = {}
            paths = [
                Path(url.toLocalFile())
                for url in mime.urls()
                if url.isLocalFile() and Path(url.toLocalFile()).exists()
            ]
            links = [
                url.toString()
                for url in mime.urls()
                if not url.isLocalFile()
                and url.isValid()
                and url.scheme().casefold() in {"http", "https", "ftp"}
            ]
            if html_link and html_link not in links:
                links.append(html_link)
            rejected_oversized_item = False
            if paths or links:
                for path in paths:
                    content = str(path)
                    if self.enforce_size_limit and (
                        is_oversized_text(content) or is_oversized_image_file(path)
                    ):
                        rejected_oversized_item = True
                        continue
                    try:
                        self.db.insert_with_type(content, "path")
                        self.path_copied.emit(content)
                    except Exception:
                        log_exception("Failed to store clipboard path")
                for content in links:
                    if self.enforce_size_limit and is_oversized_text(content):
                        rejected_oversized_item = True
                        continue
                    if not content:
                        continue
                    self._last_text = content
                    try:
                        self.db.insert_with_type(content, "link")
                        self.text_copied.emit(content)
                    except Exception:
                        log_exception("Failed to store clipboard link")
                if rejected_oversized_item:
                    self.oversized_item_rejected.emit()
                return


        if html_link:
            self._clipboard_image_snapshot = None
            self._clipboard_image_snapshot_hash = None
            self._clipboard_rich_formats_snapshot = {}
            if not self.enforce_size_limit or not is_oversized_text(html_link):
                self._last_text = html_link
                try:
                    self.db.insert_with_type(html_link, "link")
                    self.text_copied.emit(html_link)
                except Exception:
                    log_exception("Failed to store clipboard HTML link")
            else:
                self.oversized_item_rejected.emit()
            return

        if not mime.hasText():
            self._clipboard_image_snapshot = None
            self._clipboard_image_snapshot_hash = None
            self._clipboard_rich_formats_snapshot = {}
            if self.enforce_size_limit and mime.hasHtml() and is_oversized_text(mime.html()):
                self.oversized_item_rejected.emit()
            return

        raw_text = mime.text()
        self._clipboard_image_snapshot = None
        self._clipboard_image_snapshot_hash = None
        self._clipboard_rich_formats_snapshot = {}
        if self._is_vector_markup(raw_text, mime):
            self._last_text = raw_text
            return
        if self.enforce_size_limit and (is_oversized_text(raw_text) or (
            mime.hasHtml() and is_oversized_text(mime.html())
        )):
            if raw_text != self._last_text:
                self.oversized_item_rejected.emit()
            self._last_text = raw_text
            return

        text = raw_text.strip()
        if not text:
            return

        self._last_text = text
        try:
            path = Path(text)
            if path.exists():
                if self.enforce_size_limit and (
                    is_oversized_text(text) or is_oversized_image_file(path)
                ):
                    self.oversized_item_rejected.emit()
                    return
                self.db.insert_with_type(text, "path")
                self.path_copied.emit(text)
            else:
                self.db.insert(text)
                self.text_copied.emit(text)
        except Exception:
            log_exception("Failed to store text clipboard item")

    @staticmethod
    def _single_copied_html_link(mime):
        """Extract a link from browser 'copy link' HTML, without importing page links."""
        if not mime.hasHtml():
            return None

        class AnchorParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.hrefs = []
                self.visible_text = []
                self._inside_anchor = False

            def handle_starttag(self, tag, attrs):
                if tag.casefold() == "a":
                    self._inside_anchor = True
                    href = dict(attrs).get("href")
                    if href:
                        self.hrefs.append(href.strip())

            def handle_endtag(self, tag):
                if tag.casefold() == "a":
                    self._inside_anchor = False

            def handle_data(self, data):
                if self._inside_anchor:
                    self.visible_text.append(data)

        parser = AnchorParser()
        try:
            parser.feed(mime.html())
        except Exception:
            return None
        if len(parser.hrefs) != 1:
            return None

        from PySide6.QtCore import QUrl

        url = QUrl(parser.hrefs[0])
        if not url.isValid() or url.scheme().casefold() not in {"http", "https", "ftp"}:
            return None
        selected_text = " ".join(" ".join(parser.visible_text).split())
        clipboard_text = " ".join(mime.text().split()) if mime.hasText() else ""
        if selected_text and clipboard_text != selected_text:
            return None
        return url.toString()

    @staticmethod
    def _clipboard_image_source_url(mime):
        """Find an image URL when a browser supplies a reference but no pixels."""
        candidates = []
        if mime.hasUrls():
            candidates.extend(
                (url.toString(), False)
                for url in mime.urls()
                if not url.isLocalFile() and url.isValid()
            )
        if mime.hasText():
            text_candidate = mime.text().strip()
            if text_candidate.startswith(("http://", "https://")):
                candidates.append((text_candidate, False))

        if mime.hasHtml():
            class ImageSourceParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.sources = []
                    self.visible_text = []

                def handle_starttag(self, tag, attrs):
                    if tag.casefold() == "img":
                        source = dict(attrs).get("src")
                        if source:
                            self.sources.append(source.strip())

                def handle_data(self, data):
                    self.visible_text.append(data)

            parser = ImageSourceParser()
            try:
                parser.feed(mime.html())
                if len(parser.sources) == 1 and not " ".join(" ".join(parser.visible_text).split()):
                    candidates.extend((source, True) for source in parser.sources)
            except Exception:
                pass

        image_extensions = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".avif")
        for candidate, explicitly_image in candidates:
            try:
                parsed = urlsplit(candidate)
                query = parse_qs(parsed.query)
                image_targets = query.get("imgurl") or query.get("mediaurl") or []
                target = image_targets[0] if image_targets else candidate
                target_parsed = urlsplit(target)
                if target_parsed.scheme.casefold() not in {"http", "https"}:
                    continue
                is_image_target = (
                    explicitly_image
                    or bool(image_targets)
                    or target_parsed.path.casefold().endswith(image_extensions)
                )
                if is_image_target:
                    return target
            except (TypeError, ValueError):
                continue
        return None

    def _queue_remote_image(self, image_url):
        self._clipboard_image_snapshot = None
        self._clipboard_image_snapshot_hash = None
        self._clipboard_rich_formats_snapshot = {}
        reserved_path = self._reserve_image_record()
        if reserved_path is None:
            return
        self._image_executor.submit(
            self._download_remote_image, image_url, reserved_path
        )

    def _reserve_image_record(self):
        """Insert an image history row at copy time, before slow image work."""
        image_path = self.image_store.reserve_image_path()
        try:
            record_id = self.db.insert_with_type(image_path, "img")
            if record_id is None:
                raise RuntimeError("Could not reserve an image history row")
            with self._reserved_image_records_lock:
                self._reserved_image_records[image_path] = record_id
            return image_path
        except Exception:
            log_exception("Failed to reserve clipboard image history position")
            return None

    def _discard_reserved_image_record(self, image_path):
        if not image_path:
            return
        with self._reserved_image_records_lock:
            self._reserved_image_records.pop(image_path, None)
        try:
            self.db.delete_by_content(image_path)
        except Exception:
            log_exception("Failed to remove incomplete clipboard image history row")
        try:
            Path(image_path).unlink(missing_ok=True)
            Path(f"{image_path}.mime.json").unlink(missing_ok=True)
        except OSError:
            log_exception("Failed to remove incomplete clipboard image file")

    def _download_remote_image(self, image_url, reserved_path):
        """Fetch a browser-copied image reference and store its decoded pixels."""
        try:
            # Resolve and pin the destination before connecting. Reject private
            # addresses and revalidate each redirect to avoid clipboard-driven
            # requests into localhost or private networks.
            _resolve_public_http_url(image_url)
            opener = build_opener(
                ProxyHandler({}),
                _PublicHTTPHandler(),
                _PublicHTTPSHandler(),
                _PublicRedirectHandler(),
            )
            request = Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
            with opener.open(request, timeout=10) as response:
                payload = response.read(MAX_CLIP_ITEM_SIZE_BYTES + 1)
            if len(payload) > MAX_CLIP_ITEM_SIZE_BYTES:
                if self.enforce_size_limit:
                    self.oversized_item_rejected.emit()
                return

            image = QImage.fromData(payload)
            if image.isNull():
                return
            source_size_bytes = self.image_store.image_payload_size(image)
            if source_size_bytes is None:
                return
            if self.enforce_size_limit and source_size_bytes > MAX_CLIP_ITEM_SIZE_BYTES:
                self.oversized_item_rejected.emit()
                return
            self._last_image_cache_key = image.cacheKey()
            self._process_image(
                image,
                source_size_bytes=source_size_bytes,
                reserved_path=reserved_path,
            )
        except Exception:
            log_exception("Failed to fetch copied image from browser URL")
        finally:
            if not Path(reserved_path).is_file():
                self._discard_reserved_image_record(reserved_path)

    @staticmethod
    def _is_vector_markup(text, mime):
        sample = str(text).lstrip()[:20000].lower()
        formats = " ".join(str(item).lower() for item in mime.formats())
        return (
            (sample.startswith("<?xml") and "<svg" in sample)
            or sample.startswith("<svg")
            or ("svg" in formats and ("<?xml" in sample or "<svg" in sample))
        )

    @staticmethod
    def _capture_rich_formats(mime):
        """Capture non-raster formats needed to round-trip editable objects."""
        formats = {}
        total_bytes = 0
        try:
            for raw_format in mime.formats():
                format_name = str(raw_format)
                normalized = format_name.lower()
                if normalized == "application/x-qt-image" or any(
                    marker in normalized
                    for marker in (
                        'value="cf_dib"',
                        'value="cf_dibv5"',
                        'value="cf_bitmap"',
                    )
                ):
                    continue
                if normalized.startswith("image/") and not any(
                    marker in normalized for marker in ("svg", "emf", "wmf", "metafile")
                ):
                    continue
                payload = bytes(mime.data(raw_format))
                if not payload:
                    continue
                total_bytes += len(payload)
                if total_bytes > MAX_PERSISTED_RICH_FORMAT_BYTES:
                    return {}
                formats[format_name] = payload
        except Exception:
            log_exception("Failed to capture rich clipboard formats")
            return {}
        return formats

    @staticmethod
    def _mime_data_with_image(formats, image):
        mime_data = QMimeData()
        for format_name, payload in formats.items():
            mime_data.setData(format_name, QByteArray(payload))
        mime_data.setImageData(image)
        return mime_data

    @staticmethod
    def _rich_formats_sidecar_path(image_path):
        return Path(f"{image_path}.mime.json")

    def _save_rich_formats(self, image_path, formats):
        if not formats:
            return
        sidecar_path = self._rich_formats_sidecar_path(image_path)
        try:
            sidecar_path.parent.mkdir(parents=True, exist_ok=True)
            encoded = {
                name: base64.b64encode(payload).decode("ascii")
                for name, payload in formats.items()
            }
            with sidecar_path.open("w", encoding="utf-8") as sidecar:
                json.dump({"version": 1, "formats": encoded}, sidecar)
            self._rich_formats_by_image_path[str(Path(image_path).resolve())] = formats
        except Exception:
            log_exception("Failed to persist rich clipboard formats")

    def _load_rich_formats(self, image_path):
        key = str(Path(image_path).resolve())
        cached = self._rich_formats_by_image_path.get(key)
        if cached is not None:
            return cached
        sidecar_path = self._rich_formats_sidecar_path(image_path)
        try:
            with sidecar_path.open("r", encoding="utf-8") as sidecar:
                stored = json.load(sidecar)
            if stored.get("version") != 1 or not isinstance(stored.get("formats"), dict):
                return {}
            decoded = {
                name: base64.b64decode(payload, validate=True)
                for name, payload in stored["formats"].items()
            }
            self._rich_formats_by_image_path[key] = decoded
            return decoded
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {}

    def _process_image(
        self, image, image_hash=None, reserved=False, source_size_bytes=None, rich_formats=None,
        clipboard_metadata=None, reserved_path=None,
    ):
        stored = False
        owns_pending_hash = False
        try:
            image_cache_key = image.cacheKey()
            image_hash = image_hash or self._hash_image(image)
            if not image_hash:
                return

            ignored_until = self._ignored_image_hashes.get(image_hash)
            if ignored_until is not None:
                if monotonic() <= ignored_until:
                    return
                self._ignored_image_hashes.pop(image_hash, None)

            with self._image_lock:
                if image_hash == self._last_image_hash:
                    if clipboard_metadata:
                        sequence, owner_name, formats = clipboard_metadata[:3]
                        get_logger().info(
                            "Ignored exact duplicate image clipboard update "
                            "(sequence=%s, owner=%s, formats=%s)",
                            sequence,
                            owner_name or "unknown",
                            ", ".join(formats) or "none",
                        )
                    return
                if not reserved and image_hash in self._pending_image_hashes:
                    # Keep the latest matching clipboard update until the
                    # original worker finishes. This lets it mark the hash as
                    # current even if its own cache key is already stale.
                    sequence = clipboard_metadata[0] if clipboard_metadata else None
                    self._pending_image_updates[image_hash] = (
                        sequence,
                        image_cache_key,
                    )
                    return
                self._pending_image_hashes.add(image_hash)
                owns_pending_hash = True
                sequence = clipboard_metadata[0] if clipboard_metadata else None
                self._pending_image_updates[image_hash] = (
                    sequence,
                    image_cache_key,
                )

            image_path = self.image_store.save_image(
                image,
                "screenshot",
                source_size_bytes,
                target_path=reserved_path,
            )
            if not image_path:
                return

            if reserved_path is not None:
                with self._reserved_image_records_lock:
                    record_id = self._reserved_image_records.get(reserved_path)
                if record_id is None or self.db.get_by_id(record_id) is None:
                    return

            image_file = Path(image_path)
            if (self.enforce_size_limit and image_file.is_file()
                    and image_file.stat().st_size > MAX_CLIP_ITEM_SIZE_BYTES):
                image_file.unlink(missing_ok=True)
                self.oversized_item_rejected.emit()
                return

            if reserved_path is None:
                self.db.insert_with_type(image_path, "img")
            if rich_formats:
                self._save_rich_formats(image_path, rich_formats)
            stored = True
            if reserved_path is not None:
                with self._reserved_image_records_lock:
                    self._reserved_image_records.pop(reserved_path, None)
            with self._image_lock:
                latest_update = self._pending_image_updates.get(image_hash)
                latest_update_is_current = latest_update is not None and (
                    latest_update[1] == self._last_image_cache_key
                    or (
                        latest_update[0] is not None
                        and latest_update[0] == self._last_notified_clipboard_sequence
                    )
                )
                if (
                    clipboard_metadata is None
                    or image_cache_key == self._last_image_cache_key
                    or latest_update_is_current
                    or (
                        len(clipboard_metadata) > 3
                        and clipboard_metadata[3] == self._clipboard_image_epoch
                    )
                ):
                    self._last_image_hash = image_hash
            snapshot = self._clipboard_image_snapshot
            if snapshot is not None and image_cache_key == snapshot.cacheKey():
                self._clipboard_image_snapshot_hash = image_hash
            self.image_copied.emit(image_path)
        except Exception:
            log_exception("Failed to process clipboard image")
        finally:
            if image_hash and owns_pending_hash:
                with self._image_lock:
                    self._pending_image_hashes.discard(image_hash)
                    self._pending_image_updates.pop(image_hash, None)
            if reserved_path is not None and not stored:
                self._discard_reserved_image_record(reserved_path)

    def _hash_image(self, image):
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        if not image.save(buffer, "PNG"):
            return None
        data = bytes(buffer.data())
        return sha256(data).hexdigest()

    @staticmethod
    def _windows_clipboard_sequence_number():
        """Return Windows' sequence number for the current clipboard contents."""
        if os.name != "nt":
            return None
        try:
            user32 = ctypes.windll.user32
            user32.GetClipboardSequenceNumber.restype = ctypes.c_uint
            return int(user32.GetClipboardSequenceNumber())
        except (AttributeError, OSError, TypeError, ValueError):
            return None

    @staticmethod
    def _windows_clipboard_owner_name():
        """Return the executable name of the process that last set the clipboard."""
        if os.name != "nt":
            return None

        process_handle = None
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            user32.GetClipboardOwner.restype = ctypes.c_void_p
            user32.GetWindowThreadProcessId.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_ulong),
            ]
            user32.GetWindowThreadProcessId.restype = ctypes.c_ulong
            kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
            kernel32.OpenProcess.restype = ctypes.c_void_p
            kernel32.QueryFullProcessImageNameW.argtypes = [
                ctypes.c_void_p,
                ctypes.c_ulong,
                ctypes.c_wchar_p,
                ctypes.POINTER(ctypes.c_ulong),
            ]
            kernel32.QueryFullProcessImageNameW.restype = ctypes.c_int
            kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel32.CloseHandle.restype = ctypes.c_int

            owner_window = user32.GetClipboardOwner()
            if not owner_window:
                return None
            process_id = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(owner_window, ctypes.byref(process_id))
            if not process_id.value:
                return None
            process_handle = kernel32.OpenProcess(0x1000, False, process_id.value)
            if not process_handle:
                return None
            executable_path = ctypes.create_unicode_buffer(32768)
            path_length = ctypes.c_ulong(len(executable_path))
            if not kernel32.QueryFullProcessImageNameW(
                process_handle, 0, executable_path, ctypes.byref(path_length)
            ):
                return None
            return os.path.basename(executable_path.value)
        except (AttributeError, OSError, TypeError, ValueError):
            return None
        finally:
            if process_handle:
                try:
                    ctypes.windll.kernel32.CloseHandle(process_handle)
                except (AttributeError, OSError):
                    pass

    def _load_paste_image(self, image_path):
        """Load and hash a saved image once, reusing recent decoded images."""
        path = Path(image_path)
        try:
            stat = path.stat()
            signature = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            signature = None

        key = str(path.resolve())
        cached = self._paste_image_cache.get(key)
        if cached is not None and cached[0] == signature:
            self._paste_image_cache.move_to_end(key)
            return cached[1], cached[2]
        if cached is not None:
            self._paste_image_cache_bytes -= cached[3]
            del self._paste_image_cache[key]

        image = QImage(str(path))
        if image.isNull():
            return image, None
        image_hash = self._hash_image(image)
        image_bytes = max(0, int(image.sizeInBytes()))
        if signature is not None and image_hash and image_bytes <= PASTE_IMAGE_CACHE_MAX_BYTES:
            self._paste_image_cache[key] = (signature, image, image_hash, image_bytes)
            self._paste_image_cache_bytes += image_bytes
            while (
                self._paste_image_cache_bytes > PASTE_IMAGE_CACHE_MAX_BYTES
                and len(self._paste_image_cache) > 1
            ):
                _, evicted = self._paste_image_cache.popitem(last=False)
                self._paste_image_cache_bytes -= evicted[3]
        return image, image_hash

    def _get_current_clipboard_text(self):
        mime = self.clipboard.mimeData()
        if mime and mime.hasText():
            return mime.text()
        return None

    def _get_current_clipboard_image(self):
        mime = self.clipboard.mimeData()
        if mime and mime.hasImage():
            image = self.clipboard.image()
            if not image.isNull():
                return image
        return None

    def close(self):
        try:
            self.clipboard.dataChanged.disconnect(self.on_data_changed)
        except (RuntimeError, TypeError):
            pass
        self._image_executor.shutdown(wait=True, cancel_futures=True)
        with self._reserved_image_records_lock:
            pending_paths = tuple(self._reserved_image_records)
        for image_path in pending_paths:
            self._discard_reserved_image_record(image_path)
