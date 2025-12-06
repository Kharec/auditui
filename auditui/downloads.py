"""Download helpers for Audible content."""

import re
from pathlib import Path
from typing import Callable

import audible
import httpx
from audible.activation_bytes import get_activation_bytes

from .constants import CACHE_DIR, DEFAULT_CODEC, DOWNLOAD_URL, MIN_FILE_SIZE

StatusCallback = Callable[[str], None]


class DownloadManager:
    """Handle retrieval and download of Audible titles."""

    def __init__(
        self, auth: audible.Authenticator, client: audible.Client, cache_dir: Path = CACHE_DIR
    ) -> None:
        self.auth = auth
        self.client = client
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

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
            response = httpx.get(
                url=DOWNLOAD_URL,
                params=params,
                follow_redirects=False,
                auth=self.auth,
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
            with httpx.stream("GET", url) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(dest_path, "wb") as file_handle:
                    for chunk in response.iter_bytes(chunk_size=8192):
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

