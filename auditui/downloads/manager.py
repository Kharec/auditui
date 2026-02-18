"""Obtains AAX files from Audible (cache or download) and provides activation bytes."""

import re
from pathlib import Path
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
        self.client = client
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = chunk_size
        self._http_client = httpx.Client(
            auth=auth, timeout=30.0, follow_redirects=True)
        self._download_client = httpx.Client(
            timeout=httpx.Timeout(connect=30.0, read=None,
                                  write=30.0, pool=30.0),
            follow_redirects=True,
        )

    def get_or_download(
        self, asin: str, notify: StatusCallback | None = None
    ) -> Path | None:
        """Return local path to AAX file; download and cache if not present."""
        title = self._get_name_from_asin(asin) or asin
        safe_title = self._sanitize_filename(title)
        local_path = self.cache_dir / f"{safe_title}.aax"

        if local_path.exists() and local_path.stat().st_size >= MIN_FILE_SIZE:
            if notify:
                notify(f"Using cached file: {local_path.name}")
            return local_path

        if notify:
            notify(f"Downloading to {local_path.name}...")

        dl_link = self._get_download_link(asin, notify=notify)
        if not dl_link:
            if notify:
                notify("Failed to get download link")
            return None

        if not self._validate_download_url(dl_link):
            if notify:
                notify("Invalid download URL")
            return None

        if not self._download_file(dl_link, local_path, notify):
            if notify:
                notify("Download failed")
            return None

        if not local_path.exists() or local_path.stat().st_size < MIN_FILE_SIZE:
            if notify:
                notify("Download failed or file too small")
            return None

        return local_path

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
        title = self._get_name_from_asin(asin) or asin
        safe_title = self._sanitize_filename(title)
        local_path = self.cache_dir / f"{safe_title}.aax"
        if local_path.exists() and local_path.stat().st_size >= MIN_FILE_SIZE:
            return local_path
        return None

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
        """Remove invalid characters from filename."""
        return re.sub(r'[<>:"/\\|?*]', "_", filename)

    def _get_name_from_asin(self, asin: str) -> str | None:
        """Get the title/name of a book from its ASIN."""
        try:
            product_info = self.client.get(
                path=f"1.0/catalog/products/{asin}",
                response_groups="product_desc,product_attrs",
            )
            product = product_info.get("product", {})
            return product.get("title") or "Unknown Title"
        except (OSError, ValueError, KeyError):
            return None

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

            tld = self.auth.locale.domain
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
                downloaded = 0

                with open(dest_path, "wb") as file_handle:
                    for chunk in response.iter_bytes(chunk_size=self.chunk_size):
                        file_handle.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and notify:
                            percent = (downloaded / total_size) * 100
                            downloaded_mb = downloaded / (1024 * 1024)
                            total_mb = total_size / (1024 * 1024)
                            notify(
                                f"Downloading: {percent:.1f}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)"
                            )

            return dest_path
        except httpx.HTTPStatusError as exc:
            if notify:
                notify(
                    f"Download HTTP error: {exc.response.status_code} {exc.response.reason_phrase}"
                )
            try:
                if dest_path.exists() and dest_path.stat().st_size < MIN_FILE_SIZE:
                    dest_path.unlink()
            except OSError:
                pass
            return None
        except httpx.HTTPError as exc:
            if notify:
                notify(f"Download network error: {exc!s}")
            try:
                if dest_path.exists() and dest_path.stat().st_size < MIN_FILE_SIZE:
                    dest_path.unlink()
            except OSError:
                pass
            return None
        except (OSError, ValueError, KeyError) as exc:
            if notify:
                notify(f"Download error: {exc!s}")
            try:
                if dest_path.exists() and dest_path.stat().st_size < MIN_FILE_SIZE:
                    dest_path.unlink()
            except OSError:
                pass
            return None

    def close(self) -> None:
        """Close internal HTTP clients. Safe to call multiple times."""
        if hasattr(self, "_http_client"):
            self._http_client.close()
        if hasattr(self, "_download_client"):
            self._download_client.close()
