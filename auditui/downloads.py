"""Download helpers for Audible content."""

import re
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import audible
import httpx
from audible.activation_bytes import get_activation_bytes

from .constants import CACHE_DIR, DEFAULT_CHUNK_SIZE, DEFAULT_CODEC, DOWNLOAD_URL, MIN_FILE_SIZE

StatusCallback = Callable[[str], None]


class DownloadManager:
    """Handle retrieval and download of Audible titles."""

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
            auth=auth, timeout=30.0, follow_redirects=False)

    def get_or_download(self, asin: str, notify: StatusCallback | None = None) -> Path | None:
        """Get local path of AAX file, downloading if missing."""
        title = self._get_name_from_asin(asin) or asin
        safe_title = self._sanitize_filename(title)
        local_path = self.cache_dir / f"{safe_title}.aax"

        if local_path.exists() and local_path.stat().st_size >= MIN_FILE_SIZE:
            if notify:
                notify(f"Using cached file: {local_path.name}")
            return local_path

        if notify:
            notify(f"Downloading to {local_path.name}...")

        dl_link = self._get_download_link(asin)
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
        """Get activation bytes as hex string."""
        try:
            activation_bytes = get_activation_bytes(self.auth)
            if isinstance(activation_bytes, bytes):
                return activation_bytes.hex()
            return str(activation_bytes)
        except Exception:
            return None

    def _validate_download_url(self, url: str) -> bool:
        """Validate that the URL is a valid HTTP/HTTPS URL."""
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
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
        except Exception:
            return None

    def _get_download_link(self, asin: str, codec: str = DEFAULT_CODEC) -> str | None:
        """Get download link for book."""
        if self.auth.adp_token is None:
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
                return None

            tld = self.auth.locale.domain
            return link.replace("cds.audible.com", f"cds.audible.{tld}")

        except Exception:
            return None

    def _download_file(
        self, url: str, dest_path: Path, notify: StatusCallback | None = None
    ) -> Path | None:
        """Download file from URL to destination."""
        try:
            with self._http_client.stream("GET", url) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(dest_path, "wb") as file_handle:
                    for chunk in response.iter_bytes(chunk_size=self.chunk_size):
                        file_handle.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and notify:
                            percent = (downloaded / total_size) * 100
                            notify(
                                f"Downloading: {percent:.1f}% ({downloaded}/{total_size} bytes)"
                            )

            return dest_path
        except Exception:
            return None

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        if hasattr(self, "_http_client"):
            self._http_client.close()
