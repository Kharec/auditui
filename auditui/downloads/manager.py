"""Obtains AAX files from Audible (cache or download) and provides activation bytes."""

import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import audible
import httpx
from audible.activation_bytes import get_activation_bytes

from ..constants import (
    CACHE_DIR,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CODEC,
    DOWNLOAD_URL,
    MIN_FILE_SIZE,
)
from ..types import StatusCallback


class DownloadManager:
    """Obtains AAX files from Audible (cache or download) and provides activation bytes."""

    def __init__(
        self,
        auth: audible.Authenticator,
        client: audible.Client,
        cache_dir: Path = CACHE_DIR,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> None:
        self.auth = auth
        self.client: Any = client
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = chunk_size
        self._http_client = httpx.Client(auth=auth, timeout=30.0, follow_redirects=True)
        self._download_client = httpx.Client(
            timeout=httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0),
            follow_redirects=True,
        )

    def get_or_download(
        self,
        asin: str,
        notify: StatusCallback | None = None,
        preferred_title: str | None = None,
        preferred_author: str | None = None,
    ) -> Path | None:
        """Return local path to AAX file; download and cache if not present."""
        filename_stems = self._get_filename_stems_from_asin(
            asin,
            preferred_title=preferred_title,
            preferred_author=preferred_author,
        )
        local_path = self.cache_dir / f"{filename_stems[0]}.aax"
        cached_path = self._find_cached_path(filename_stems)
        if cached_path:
            if notify:
                notify(f"Using cached file: {cached_path.name}")
            return cached_path

        if notify:
            notify(f"Downloading to {local_path.name}...")

        if not self._download_to_valid_file(asin, local_path, notify):
            return None

        return local_path

    def _download_to_valid_file(
        self,
        asin: str,
        local_path: Path,
        notify: StatusCallback | None = None,
    ) -> bool:
        """Download with one retry and ensure resulting file has a valid size."""
        for attempt in range(1, 3):
            if not self._attempt_download(asin, local_path, notify):
                return False
            if local_path.exists() and local_path.stat().st_size >= MIN_FILE_SIZE:
                return True

            downloaded_size = local_path.stat().st_size if local_path.exists() else 0
            if notify and attempt == 1:
                notify(
                    f"Downloaded file too small ({downloaded_size} bytes), retrying..."
                )
            if notify and attempt == 2:
                notify(
                    f"Download failed: file too small ({downloaded_size} bytes, expected >= {MIN_FILE_SIZE})"
                )
            self._cleanup_partial_file(local_path)

        return False

    def _attempt_download(
        self,
        asin: str,
        local_path: Path,
        notify: StatusCallback | None = None,
    ) -> bool:
        """Perform one download attempt including link lookup and URL validation."""
        dl_link = self._get_download_link(asin, notify=notify)
        if not dl_link:
            if notify:
                notify("Failed to get download link")
            return False

        if not self._validate_download_url(dl_link):
            if notify:
                notify("Invalid download URL")
            return False

        if not self._download_file(dl_link, local_path, notify):
            if notify:
                notify("Download failed")
            return False

        return True

    def get_activation_bytes(self) -> str | None:
        """Return activation bytes as hex string for ffplay/ffmpeg."""
        try:
            activation_bytes = get_activation_bytes(self.auth)
            if isinstance(activation_bytes, bytes):
                return activation_bytes.hex()
            return str(activation_bytes)
        except (OSError, ValueError, KeyError, AttributeError):
            return None

    def get_cached_path(self, asin: str) -> Path | None:
        """Return path to cached AAX file if it exists and is valid size."""
        return self._find_cached_path(self._get_filename_stems_from_asin(asin))

    def is_cached(self, asin: str) -> bool:
        """Return True if the title is present in cache with valid size."""
        return self.get_cached_path(asin) is not None

    def remove_cached(self, asin: str, notify: StatusCallback | None = None) -> bool:
        """Delete the cached AAX file for the given ASIN. Returns True on success."""
        cached_path = self.get_cached_path(asin)
        if not cached_path:
            if notify:
                notify("Book is not cached")
            return False

        try:
            cached_path.unlink()
            if notify:
                notify(f"Removed from cache: {cached_path.name}")
            return True
        except OSError as exc:
            if notify:
                notify(f"Failed to remove cache: {exc}")
            return False

    def _validate_download_url(self, url: str) -> bool:
        """Validate that the URL is a valid HTTP/HTTPS URL."""
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except (ValueError, AttributeError):
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """Normalize a filename segment with ASCII letters, digits, and dashes."""
        ascii_text = unicodedata.normalize("NFKD", filename)
        ascii_text = ascii_text.encode("ascii", "ignore").decode("ascii")
        ascii_text = re.sub(r"[’'`]+", "", ascii_text)
        ascii_text = re.sub(r"[^A-Za-z0-9]+", "-", ascii_text)
        ascii_text = re.sub(r"-+", "-", ascii_text)
        ascii_text = ascii_text.strip("-._")
        return ascii_text or "Unknown"

    def _find_cached_path(self, filename_stems: list[str]) -> Path | None:
        """Return the first valid cached path matching any candidate filename stem."""
        for filename_stem in filename_stems:
            local_path = self.cache_dir / f"{filename_stem}.aax"
            if local_path.exists() and local_path.stat().st_size >= MIN_FILE_SIZE:
                return local_path
        return None

    def _get_filename_stems_from_asin(
        self,
        asin: str,
        preferred_title: str | None = None,
        preferred_author: str | None = None,
    ) -> list[str]:
        """Build preferred and fallback cache filename stems for an ASIN."""
        if preferred_title:
            preferred_combined = (
                f"{self._sanitize_filename(preferred_author or 'Unknown Author')}_"
                f"{self._sanitize_filename(preferred_title)}"
            )
            preferred_legacy = self._sanitize_filename(preferred_title)
            fallback_asin = self._sanitize_filename(asin)
            return list(
                dict.fromkeys([preferred_combined, preferred_legacy, fallback_asin])
            )

        try:
            product_info = self.client.get(
                path=f"1.0/catalog/products/{asin}",
                **{"response_groups": "contributors,product_desc,product_attrs"},
            )
            product = product_info.get("product", {})
            title = product.get("title") or "Unknown Title"
            author = self._get_primary_author(product)
            combined = (
                f"{self._sanitize_filename(author)}_{self._sanitize_filename(title)}"
            )
            legacy_title = self._sanitize_filename(title)
            fallback_asin = self._sanitize_filename(asin)
            return list(dict.fromkeys([combined, legacy_title, fallback_asin]))
        except (OSError, ValueError, KeyError, AttributeError):
            return [self._sanitize_filename(asin)]

    def _get_primary_author(self, product: dict) -> str:
        """Extract a primary author name from product metadata."""
        contributors = product.get("authors") or product.get("contributors") or []
        for contributor in contributors:
            if not isinstance(contributor, dict):
                continue
            name = contributor.get("name")
            if isinstance(name, str) and name.strip():
                return name
        return "Unknown Author"

    def _get_download_link(
        self,
        asin: str,
        codec: str = DEFAULT_CODEC,
        notify: StatusCallback | None = None,
    ) -> str | None:
        """Obtain CDN download URL for the given ASIN and codec."""
        if self.auth.adp_token is None:
            if notify:
                notify("Missing ADP token (not authenticated?)")
            return None

        try:
            params = {
                "type": "AUDI",
                "currentTransportMethod": "WIFI",
                "key": asin,
                "codec": codec,
            }
            response = self._http_client.get(
                url=DOWNLOAD_URL,
                params=params,
            )
            response.raise_for_status()

            link = response.headers.get("Location")
            if not link:
                link = str(response.url)

            locale = getattr(self.auth, "locale", None)
            tld = getattr(locale, "domain", "com")
            return link.replace("cds.audible.com", f"cds.audible.{tld}")

        except httpx.HTTPError as exc:
            if notify:
                notify(f"Download-link request failed: {exc!s}")
            return None
        except (OSError, ValueError, KeyError, AttributeError) as exc:
            if notify:
                notify(f"Download-link error: {exc!s}")
            return None

    def _download_file(
        self, url: str, dest_path: Path, notify: StatusCallback | None = None
    ) -> Path | None:
        """Stream download from URL to dest_path; reports progress via notify."""
        try:
            with self._download_client.stream("GET", url) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))
                self._stream_to_file(response, dest_path, total_size, notify)

            return dest_path
        except httpx.HTTPStatusError as exc:
            if notify:
                notify(
                    f"Download HTTP error: {exc.response.status_code} {exc.response.reason_phrase}"
                )
            self._cleanup_partial_file(dest_path)
            return None
        except httpx.HTTPError as exc:
            if notify:
                notify(f"Download network error: {exc!s}")
            self._cleanup_partial_file(dest_path)
            return None
        except (OSError, ValueError, KeyError) as exc:
            if notify:
                notify(f"Download error: {exc!s}")
            self._cleanup_partial_file(dest_path)
            return None

    def _stream_to_file(
        self,
        response: httpx.Response,
        dest_path: Path,
        total_size: int,
        notify: StatusCallback | None = None,
    ) -> None:
        """Write streamed response bytes to disk and emit progress messages."""
        downloaded = 0
        with open(dest_path, "wb") as file_handle:
            for chunk in response.iter_bytes(chunk_size=self.chunk_size):
                file_handle.write(chunk)
                downloaded += len(chunk)
                self._notify_download_progress(downloaded, total_size, notify)

    def _notify_download_progress(
        self,
        downloaded: int,
        total_size: int,
        notify: StatusCallback | None = None,
    ) -> None:
        """Emit a formatted progress message when total size is known."""
        if total_size <= 0 or not notify:
            return
        percent = (downloaded / total_size) * 100
        downloaded_mb = downloaded / (1024 * 1024)
        total_mb = total_size / (1024 * 1024)
        notify(f"Downloading: {percent:.1f}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)")

    def _cleanup_partial_file(self, dest_path: Path) -> None:
        """Remove undersized partial download files after transfer failures."""
        try:
            if dest_path.exists() and dest_path.stat().st_size < MIN_FILE_SIZE:
                dest_path.unlink()
        except OSError:
            return

    def close(self) -> None:
        """Close internal HTTP clients. Safe to call multiple times."""
        if hasattr(self, "_http_client"):
            self._http_client.close()
        if hasattr(self, "_download_client"):
            self._download_client.close()
