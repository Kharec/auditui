#!/usr/bin/env python3
"""Player playground for Audible TUI - download and play a specific track"""

import argparse
import json
import logging
import re
import shutil
import subprocess
import sys
from getpass import getpass
from pathlib import Path

import audible
import httpx
from audible.activation_bytes import get_activation_bytes


MIN_FILE_SIZE = 1024 * 1024
DOWNLOAD_URL = "https://cde-ta-g7g.amazon.com/FionaCDEServiceEngine/FSDownloadContent"
DEFAULT_CODEC = "LC_128_44100_stereo"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

logging.getLogger("audible").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename."""
    return re.sub(r'[<>:"/\\|?*]', "_", filename)


class AudiblePlayer:
    """Class to handle Audible authentication, downloading, and playback."""

    def __init__(self) -> None:
        """Initialize the player with authentication."""
        self.auth: audible.Authenticator | None = None
        self.client: audible.Client | None = None
        self.home = Path.home()
        self.cache_dir = self.home / ".cache" / "auditui" / "books"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def authenticate(self) -> None:
        """Authenticate with Audible and store auth and client."""
        auth_path = self.home / ".config" / "auditui" / "auth.json"
        auth_path.parent.mkdir(parents=True, exist_ok=True)

        if auth_path.exists():
            try:
                self.auth = audible.Authenticator.from_file(str(auth_path))
                self.client = audible.Client(auth=self.auth)
                return
            except Exception:
                logger.info(
                    "Failed to load existing auth. Re-authenticating.\n")

        email = input("Email: ")
        password = getpass("Password: ")
        marketplace = (
            input("Marketplace locale (default: US): ").strip().upper() or "US"
        )

        self.auth = audible.Authenticator.from_login(
            username=email, password=password, locale=marketplace
        )
        self.auth.to_file(str(auth_path))
        self.client = audible.Client(auth=self.auth)

    def get_name_from_asin(self, asin: str) -> str | None:
        """Get the title/name of a book from its ASIN."""
        try:
            product_info = self.client.get(
                path=f"1.0/catalog/products/{asin}",
                response_groups="product_desc,product_attrs",
            )
            product = product_info.get("product", {})
            return product.get("title") or "Unknown Title"
        except Exception as e:
            logger.error(f"Error getting name for ASIN {asin}: {e}")
            return None

    def get_download_link(self, asin: str, codec: str = DEFAULT_CODEC) -> str | None:
        """Get download link for book using the example method."""
        if self.auth.adp_token is None:
            raise Exception("No adp token present. Can't get download link.")

        try:
            params = {
                "type": "AUDI",
                "currentTransportMethod": "WIFI",
                "key": asin,
                "codec": codec,
            }
            r = httpx.get(
                url=DOWNLOAD_URL, params=params, follow_redirects=False, auth=self.auth
            )
            r.raise_for_status()

            link = r.headers.get("Location")
            if not link:
                raise ValueError("No Location header in response")

            tld = self.auth.locale.domain
            new_link = link.replace("cds.audible.com", f"cds.audible.{tld}")
            return new_link
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting download link: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting download link: {e}")
            return None

    def download_file(self, url: str, dest_path: Path) -> Path | None:
        """Download file from URL to destination."""
        try:
            with httpx.stream("GET", url) as r:
                r.raise_for_status()
                total_size = int(r.headers.get("content-length", 0))
                downloaded = 0

                with open(dest_path, "wb") as f:
                    for chunk in r.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(
                                f"\rDownloading: {percent:.1f}% ({downloaded}/{total_size} bytes)",
                                end="",
                                flush=True,
                            )

            print()
            return dest_path
        except httpx.HTTPError as e:
            logger.error(f"\nHTTP error downloading file: {e}")
            return None
        except Exception as e:
            logger.error(f"\nError downloading file: {e}")
            return None

    def get_or_download(self, asin: str) -> Path | None:
        """Get local path of AAX file, downloading if missing."""
        title = self.get_name_from_asin(asin)
        if not title:
            title = asin

        safe_title = sanitize_filename(title)
        local_path = self.cache_dir / f"{safe_title}.aax"

        if local_path.exists() and local_path.stat().st_size >= MIN_FILE_SIZE:
            logger.info(f"Using cached file: {local_path.name}")
            return local_path

        logger.info(f"\nDownloading to {local_path.name}...")
        dl_link = self.get_download_link(asin)
        if not dl_link:
            return None

        if not self.download_file(dl_link, local_path):
            return None

        if not local_path.exists() or local_path.stat().st_size < MIN_FILE_SIZE:
            logger.error("Download failed or file too small.")
            return None

        return local_path

    def fetch_library(self) -> list[dict]:
        """Fetch all library items from Audible API."""
        response_groups = (
            "contributors,media,product_attrs,product_desc,product_details,"
            "rating,is_finished,listening_status,percent_complete"
        )
        all_items = []
        page = 1
        page_size = 50

        while True:
            library = self.client.get(
                path="library",
                num_results=page_size,
                page=page,
                response_groups=response_groups,
            )
            items = library.get("items", [])
            if not items:
                break
            all_items.extend(items)
            logger.debug(f"Fetched page {page} ({len(items)} items)...")
            if len(items) < page_size:
                break
            page += 1

        return all_items

    def extract_asin(self, item: dict) -> str | None:
        """Extract ASIN from library item."""
        product = item.get("product", {})
        return item.get("asin") or product.get("asin")

    def extract_title(self, item: dict) -> str:
        """Extract title from library item."""
        product = item.get("product", {})
        return (
            product.get("title")
            or item.get("title")
            or product.get("asin", "Unknown Title")
        )

    def extract_authors(self, item: dict) -> str:
        """Extract author names from library item."""
        product = item.get("product", {})
        authors = product.get("authors") or product.get("contributors") or []
        if not authors and "authors" in item:
            authors = item.get("authors", [])
        author_names = ", ".join(
            [a.get("name", "") for a in authors if isinstance(a, dict)]
        )
        return author_names or "Unknown"

    def extract_progress(self, item: dict) -> float:
        """Extract progress percentage from library item."""
        percent_complete = item.get("percent_complete")
        listening_status = item.get("listening_status", {})

        if isinstance(listening_status, dict):
            if percent_complete is None:
                percent_complete = listening_status.get("percent_complete", 0)

        return float(percent_complete) if percent_complete is not None else 0.0

    def is_finished(self, item: dict) -> bool:
        """Check if a library item is finished."""
        is_finished_flag = item.get("is_finished")
        percent_complete = item.get("percent_complete")
        listening_status = item.get("listening_status")

        if isinstance(listening_status, dict):
            is_finished_flag = is_finished_flag or listening_status.get(
                "is_finished", False
            )
            if percent_complete is None:
                percent_complete = listening_status.get("percent_complete", 0)

        return bool(is_finished_flag) or (
            isinstance(percent_complete, (int, float)
                       ) and percent_complete >= 100
        )

    def list_unfinished_tracks(self) -> list[dict]:
        """List all unfinished tracks with ASIN and name."""
        logger.info("Fetching library...")
        all_items = self.fetch_library()

        unfinished = []
        for item in all_items:
            if not self.is_finished(item):
                unfinished.append(item)

        return unfinished

    def get_activation_bytes(self) -> str:
        """Get activation bytes as hex string."""
        activation_bytes = get_activation_bytes(self.auth)
        if isinstance(activation_bytes, bytes):
            return activation_bytes.hex()
        return str(activation_bytes)

    def play(self, path: Path, activation_hex: str | None = None) -> bool:
        """Play a local file using ffplay."""
        if not shutil.which("ffplay"):
            logger.error(
                "ffplay not found. Please install ffmpeg (which includes ffplay)"
            )
            return False

        cmd = ["ffplay", "-nodisp", "-autoexit"]
        if activation_hex:
            cmd.extend(["-activation_bytes", activation_hex])
        cmd.append(str(path))

        try:
            logger.info(f"Playing: {path.name}")
            logger.info("Press Ctrl+C to stop playback\n")
            subprocess.run(
                cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return True
        except KeyboardInterrupt:
            logger.info("\nPlayback stopped by user")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error playing file: {e}")
            return False
        except FileNotFoundError:
            logger.error("ffplay not found")
            return False


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download and play Audible audiobooks")
    parser.add_argument(
        "asin", nargs="?", default="", help="ASIN of the audiobook to play"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("audible").setLevel(logging.DEBUG)
        logging.getLogger("httpx").setLevel(logging.DEBUG)

    player = AudiblePlayer()
    logger.info("Authenticating...")
    player.authenticate()

    asin = args.asin

    if not asin:
        unfinished = player.list_unfinished_tracks()
        tracks = []
        for item in unfinished:
            tracks.append(
                {
                    "title": player.extract_title(item),
                    "asin": player.extract_asin(item),
                    "authors": player.extract_authors(item),
                    "progress": player.extract_progress(item),
                }
            )
        print(json.dumps(tracks, indent=2))
        sys.exit(0)

    logger.info(f"\nGetting download link for ASIN: {asin}")
    local_path = player.get_or_download(asin)

    if not local_path:
        logger.error("Could not download file.")
        sys.exit(1)

    logger.info("\nGetting activation bytes...")
    try:
        activation_hex = player.get_activation_bytes()
    except Exception as e:
        logger.error(f"Activation bytes error: {e}")
        sys.exit(1)

    logger.info("Starting playback...\n")
    if not player.play(local_path, activation_hex):
        sys.exit(1)


if __name__ == "__main__":
    main()
