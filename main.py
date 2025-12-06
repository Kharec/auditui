#!/usr/bin/env python3
"""A terminal-based user interface (TUI) client for Audible"""

import os
import re
import shutil
import signal
import subprocess
import sys
from getpass import getpass
from pathlib import Path

import audible
import httpx
from audible.activation_bytes import get_activation_bytes
from textual.app import App, ComposeResult
from textual.events import Key
from textual.widgets import DataTable, Footer, Header, Static
from textual.worker import get_current_worker
from textual import work


class AudituiApp(App):
    """Main application class for the Audible TUI app."""

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("s", "sort", "Sort by title"),
        ("r", "reverse_sort", "Reverse sort"),
        ("p", "sort_by_progress", "Sort by progress"),
        ("a", "show_all", "Show all books"),
        ("u", "show_unfinished", "Show unfinished"),
        ("enter", "play_selected", "Play selected book"),
        ("space", "toggle_playback", "Pause/Resume"),
        ("q", "quit", "Quit application"),
    ]

    CSS = """
    DataTable {
        height: 1fr;
    }
    Static {
        height: 1;
        text-align: center;
        background: $primary;
    }
    """

    AUTH_PATH = Path.home() / ".config" / "auditui" / "auth.json"
    CACHE_DIR = Path.home() / ".cache" / "auditui" / "books"
    DOWNLOAD_URL = "https://cde-ta-g7g.amazon.com/FionaCDEServiceEngine/FSDownloadContent"
    DEFAULT_CODEC = "LC_128_44100_stereo"
    MIN_FILE_SIZE = 1024 * 1024

    def __init__(self):
        super().__init__()
        self.auth = None
        self.client = None
        self.all_items = []
        self.current_items = []
        self.show_all_mode = False
        self.progress_sort_reverse = False
        self.title_column_key = None
        self.progress_column_key = None
        self.progress_column_index = 3

        self.playback_process = None
        self.is_playing = False
        self.is_paused = False
        self.current_file_path = None
        self.current_asin = None

        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Loading...", id="status")
        table = DataTable()
        table.zebra_stripes = True
        table.cursor_type = "row"
        yield table
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the table and start fetching library data."""
        table = self.query_one(DataTable)
        table.add_columns("Title", "Author", "Length", "Progress")
        column_keys = list(table.columns.keys())
        self.title_column_key = column_keys[0]
        self.progress_column_key = column_keys[3]

        if self.client:
            self.update_status("Fetching library...")
            self.fetch_library()
        else:
            self.update_status("Not authenticated. Please restart and authenticate.")

        self.set_interval(1.0, self._check_playback_status)

    def on_unmount(self) -> None:
        """Clean up on app exit."""
        self._stop_playback()

    def on_key(self, event: Key) -> None:
        """Handle key presses on DataTable."""
        if isinstance(self.focused, DataTable):
            if event.key == "enter":
                event.prevent_default()
                self.action_play_selected()
            elif event.key == "space":
                event.prevent_default()
                self.action_toggle_playback()

    def update_status(self, message: str) -> None:
        """Update the status message in the UI."""
        status = self.query_one("#status", Static)
        status.update(message)

    @work(exclusive=True, thread=True)
    def fetch_library(self) -> None:
        """Fetch all library items from Audible API in background thread."""
        worker = get_current_worker()
        if worker.is_cancelled:
            return

        try:
            response_groups = (
                "contributors,media,product_attrs,product_desc,product_details,"
                "rating,is_finished,listening_status,percent_complete"
            )
            all_items = self._fetch_all_pages(response_groups)
            self.call_from_thread(self.on_library_loaded, all_items)
        except (OSError, ValueError, KeyError) as e:
            self.call_from_thread(self.on_library_error, str(e))

    def _fetch_all_pages(self, response_groups: str) -> list:
        """Fetch all pages of library items from the API."""
        all_items = []
        page = 1
        page_size = 50

        while True:
            library = self.client.get(
                path="library",
                num_results=page_size,
                page=page,
                response_groups=response_groups
            )

            items = library.get("items", [])
            if not items:
                break

            all_items.extend(items)
            self.call_from_thread(
                self.update_status,
                f"Fetched page {page} ({len(items)} items)..."
            )

            if len(items) < page_size:
                break

            page += 1

        return all_items

    def on_library_loaded(self, items: list) -> None:
        """Handle successful library load."""
        self.all_items = items
        self.update_status(f"Loaded {len(items)} books")
        self.show_unfinished()

    def on_library_error(self, error: str) -> None:
        """Handle library fetch error."""
        self.update_status(f"Error fetching library: {error}")

    def _extract_title(self, item: dict) -> str:
        """Extract title from library item."""
        product = item.get("product", {})
        return (
            product.get("title") or
            item.get("title") or
            product.get("asin", "Unknown Title")
        )

    def _extract_authors(self, item: dict) -> str:
        """Extract author names from library item."""
        product = item.get("product", {})
        authors = product.get("authors") or product.get("contributors") or []
        if not authors and "authors" in item:
            authors = item.get("authors", [])

        author_names = [
            a.get("name", "") for a in authors if isinstance(a, dict)
        ]
        return ", ".join(author_names) or "Unknown"

    def _extract_runtime_minutes(self, item: dict) -> int | None:
        """Extract runtime in minutes from library item."""
        product = item.get("product", {})
        runtime_fields = [
            "runtime_length_min",
            "runtime_length",
            "vLength",
            "length",
            "duration"
        ]

        runtime = None
        for field in runtime_fields:
            runtime = product.get(field) or item.get(field)
            if runtime is not None:
                break

        if runtime is None:
            return None

        if isinstance(runtime, dict):
            return int(runtime.get("min", 0))
        elif isinstance(runtime, (int, float)):
            return int(runtime)

        return None

    def _extract_progress_info(self, item: dict) -> float | None:
        """Extract progress percentage from library item."""
        percent_complete = item.get("percent_complete")
        listening_status = item.get("listening_status", {})

        if isinstance(listening_status, dict) and percent_complete is None:
            percent_complete = listening_status.get("percent_complete")

        return float(percent_complete) if percent_complete is not None else None

    def _extract_asin(self, item: dict) -> str | None:
        """Extract ASIN from library item."""
        product = item.get("product", {})
        return item.get("asin") or product.get("asin")

    def _is_finished(self, item: dict) -> bool:
        """Check if a library item is finished."""
        is_finished_flag = item.get("is_finished")
        percent_complete = item.get("percent_complete")
        listening_status = item.get("listening_status")

        if isinstance(listening_status, dict):
            is_finished_flag = is_finished_flag or listening_status.get("is_finished", False)
            if percent_complete is None:
                percent_complete = listening_status.get("percent_complete", 0)

        return bool(is_finished_flag) or (
            isinstance(percent_complete, (int, float)) and percent_complete >= 100
        )

    def format_duration(self, value: int | None, unit: str = 'minutes', default_none: str | None = None) -> str | None:
        """Format duration value into human-readable string."""
        if value is None or value <= 0:
            return default_none

        if unit == 'seconds':
            total_minutes = int(value) // 60
        else:
            total_minutes = int(value)

        if total_minutes < 60:
            return f"{total_minutes} minute{'s' if total_minutes != 1 else ''}"

        hours = total_minutes // 60
        mins = total_minutes % 60
        if mins == 0:
            return f"{hours} hour{'s' if hours != 1 else ''}"
        return f"{hours} hour{'s' if hours != 1 else ''} {mins} minute{'s' if mins != 1 else ''}"

    def _populate_table(self, items: list) -> None:
        """Populate the DataTable with library items."""
        table = self.query_one(DataTable)
        table.clear()

        if not items:
            self.update_status("No books found.")
            return

        for item in items:
            title = self._extract_title(item)
            author_names = self._extract_authors(item)
            minutes = self._extract_runtime_minutes(item)
            runtime_str = self.format_duration(
                minutes, unit='minutes', default_none="Unknown length"
            )
            percent_complete = self._extract_progress_info(item)

            progress_str = "0%"
            if percent_complete is not None and percent_complete > 0:
                progress_str = f"{percent_complete:.1f}%"

            table.add_row(
                title,
                author_names or "Unknown",
                runtime_str or "Unknown",
                progress_str,
                key=title
            )

        self.current_items = items
        mode = "all" if self.show_all_mode else "unfinished"
        self.update_status(f"Showing {len(items)} books ({mode})")

    def show_all(self) -> None:
        """Display all books in the table."""
        if not self.all_items:
            return
        self.show_all_mode = True
        self._populate_table(self.all_items)

    def show_unfinished(self) -> None:
        """Display only unfinished books in the table."""
        if not self.all_items:
            return

        self.show_all_mode = False
        unfinished_items = [
            item for item in self.all_items if not self._is_finished(item)
        ]
        self._populate_table(unfinished_items)

    def action_toggle_dark(self) -> None:
        """Toggle between dark and light theme."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def action_sort(self) -> None:
        """Sort table by title in ascending order."""
        table = self.query_one(DataTable)
        if table.row_count > 0:
            table.sort(self.title_column_key)

    def action_reverse_sort(self) -> None:
        """Sort table by title in descending order."""
        table = self.query_one(DataTable)
        if table.row_count > 0:
            table.sort(self.title_column_key, reverse=True)

    def action_sort_by_progress(self) -> None:
        """Sort table by progress percentage, toggling direction on each press."""
        table = self.query_one(DataTable)
        if table.row_count > 0:
            self.progress_sort_reverse = not self.progress_sort_reverse

            def progress_key(row_values):
                progress_cell = row_values[self.progress_column_index]
                if isinstance(progress_cell, str):
                    try:
                        return float(progress_cell.rstrip("%"))
                    except (ValueError, AttributeError):
                        return 0.0
                return 0.0

            table.sort(key=progress_key, reverse=self.progress_sort_reverse)

    def action_show_all(self) -> None:
        """Action handler to show all books."""
        self.show_all()

    def action_show_unfinished(self) -> None:
        """Action handler to show unfinished books."""
        self.show_unfinished()

    def action_play_selected(self) -> None:
        """Start playing the selected book."""
        table = self.query_one(DataTable)
        if table.row_count == 0:
            self.update_status("No books available")
            return

        cursor_row = table.cursor_row
        if cursor_row >= len(self.current_items):
            self.update_status("Invalid selection")
            return

        selected_item = self.current_items[cursor_row]
        asin = self._extract_asin(selected_item)

        if not asin:
            self.update_status("Could not get ASIN for selected book")
            return

        if self.is_playing:
            self._stop_playback()

        self.current_asin = asin
        self._start_playback_async(asin)

    def action_toggle_playback(self) -> None:
        """Toggle pause/resume state."""
        if not self.is_playing:
            self.update_status("No playback active. Press Enter to play a book.")
            return

        if not self._is_process_alive():
            self._stop_playback()
            self.update_status("Playback has ended")
            return

        if self.is_paused:
            self._resume_playback()
        else:
            self._pause_playback()

    def _get_playback_status_message(self, prefix: str) -> str:
        """Generate status message with filename if available."""
        filename = self.current_file_path.name if self.current_file_path else ""
        return f"{prefix}: {filename}" if filename else prefix

    def _check_playback_status(self) -> None:
        """Check if playback process has finished and update state accordingly."""
        if self.playback_process is None:
            return

        return_code = self.playback_process.poll()
        if return_code is not None:
            finished_file = self.current_file_path
            self.playback_process = None
            self.is_playing = False
            self.is_paused = False

            if finished_file:
                if return_code == 0:
                    self.update_status(f"Finished: {finished_file.name}")
                else:
                    self.update_status(
                        f"Playback ended unexpectedly (code: {return_code}): {finished_file.name}"
                    )
            else:
                self.update_status("Playback finished")

            self.current_file_path = None
            self.current_asin = None

    def _start_playback(self, path: Path, activation_hex: str | None = None) -> bool:
        """Start playing a local file using ffplay."""
        if not shutil.which("ffplay"):
            self.update_status("ffplay not found. Please install ffmpeg")
            return False

        if self.playback_process is not None:
            self._stop_playback()

        cmd = ["ffplay", "-nodisp", "-autoexit"]
        if activation_hex:
            cmd.extend(["-activation_bytes", activation_hex])
        cmd.append(str(path))

        try:
            self.playback_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            if self.playback_process.poll() is not None:
                return_code = self.playback_process.returncode
                self.update_status(
                    f"Playback process exited immediately (code: {return_code})"
                )
                self.playback_process = None
                return False

            self.is_playing = True
            self.is_paused = False
            self.current_file_path = path
            self.update_status(f"Playing: {path.name}")
            return True

        except Exception as e:
            self.update_status(f"Error starting playback: {e}")
            return False

    def _stop_playback(self) -> None:
        """Stop the current playback."""
        if self.playback_process is None:
            return

        try:
            if self.playback_process.poll() is None:
                self.playback_process.terminate()
                try:
                    self.playback_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.playback_process.kill()
                    self.playback_process.wait()
        except ProcessLookupError:
            pass
        except Exception:
            pass
        finally:
            self.playback_process = None
            self.is_playing = False
            self.is_paused = False
            self.current_file_path = None

    def _is_process_alive(self) -> bool:
        """Check if playback process is still running."""
        if self.playback_process is None:
            return False
        return self.playback_process.poll() is None

    def _pause_playback(self) -> None:
        """Pause the current playback."""
        if not (self.playback_process and self.is_playing and not self.is_paused):
            return

        if not self._is_process_alive():
            self._stop_playback()
            self.update_status("Playback process has ended")
            return

        try:
            os.kill(self.playback_process.pid, signal.SIGSTOP)
            self.is_paused = True
            self.update_status(self._get_playback_status_message("Paused"))
        except ProcessLookupError:
            self._stop_playback()
            self.update_status("Process no longer exists")
        except PermissionError:
            self.update_status("Permission denied: cannot pause playback")
        except Exception as e:
            self.update_status(f"Error pausing playback: {e}")

    def _resume_playback(self) -> None:
        """Resume the current playback."""
        if not (self.playback_process and self.is_playing and self.is_paused):
            return

        if not self._is_process_alive():
            self._stop_playback()
            self.update_status("Playback process has ended")
            return

        try:
            os.kill(self.playback_process.pid, signal.SIGCONT)
            self.is_paused = False
            self.update_status(self._get_playback_status_message("Playing"))
        except ProcessLookupError:
            self._stop_playback()
            self.update_status("Process no longer exists")
        except PermissionError:
            self.update_status("Permission denied: cannot resume playback")
        except Exception as e:
            self.update_status(f"Error resuming playback: {e}")

    @work(exclusive=True, thread=True)
    def _start_playback_async(self, asin: str) -> None:
        """Start playback asynchronously."""
        self.call_from_thread(self.update_status, "Preparing playback...")

        local_path = self._get_or_download(asin)
        if not local_path:
            self.call_from_thread(self.update_status, "Could not download file")
            return

        self.call_from_thread(self.update_status, "Getting activation bytes...")
        activation_hex = self._get_activation_bytes()
        if not activation_hex:
            self.call_from_thread(self.update_status, "Failed to get activation bytes")
            return

        self.call_from_thread(
            self.update_status,
            f"Starting playback of {local_path.name}..."
        )
        self.call_from_thread(self._start_playback, local_path, activation_hex)

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
                url=self.DOWNLOAD_URL,
                params=params,
                follow_redirects=False,
                auth=self.auth
            )
            response.raise_for_status()

            link = response.headers.get("Location")
            if not link:
                return None

            tld = self.auth.locale.domain
            return link.replace("cds.audible.com", f"cds.audible.{tld}")

        except Exception:
            return None

    def _download_file(self, url: str, dest_path: Path) -> Path | None:
        """Download file from URL to destination."""
        try:
            with httpx.stream("GET", url) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(dest_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            self.call_from_thread(
                                self.update_status,
                                f"Downloading: {percent:.1f}% ({downloaded}/{total_size} bytes)"
                            )

            return dest_path
        except Exception:
            return None

    def _get_or_download(self, asin: str) -> Path | None:
        """Get local path of AAX file, downloading if missing."""
        title = self._get_name_from_asin(asin) or asin
        safe_title = self._sanitize_filename(title)
        local_path = self.CACHE_DIR / f"{safe_title}.aax"

        if local_path.exists() and local_path.stat().st_size >= self.MIN_FILE_SIZE:
            self.call_from_thread(
                self.update_status,
                f"Using cached file: {local_path.name}"
            )
            return local_path

        self.call_from_thread(
            self.update_status,
            f"Downloading to {local_path.name}..."
        )

        dl_link = self._get_download_link(asin)
        if not dl_link:
            self.call_from_thread(self.update_status, "Failed to get download link")
            return None

        if not self._download_file(dl_link, local_path):
            self.call_from_thread(self.update_status, "Download failed")
            return None

        if not local_path.exists() or local_path.stat().st_size < self.MIN_FILE_SIZE:
            self.call_from_thread(
                self.update_status,
                "Download failed or file too small"
            )
            return None

        return local_path

    def _get_activation_bytes(self) -> str | None:
        """Get activation bytes as hex string."""
        try:
            activation_bytes = get_activation_bytes(self.auth)
            if isinstance(activation_bytes, bytes):
                return activation_bytes.hex()
            return str(activation_bytes)
        except Exception:
            return None


def authenticate():
    """Authenticate with Audible and return auth and client objects."""
    auth_path = Path.home() / ".config" / "auditui" / "auth.json"
    auth_path.parent.mkdir(parents=True, exist_ok=True)

    if auth_path.exists():
        try:
            authenticator = audible.Authenticator.from_file(str(auth_path))
            audible_client = audible.Client(auth=authenticator)
            return authenticator, audible_client
        except (OSError, ValueError, KeyError) as e:
            print(f"Failed to load existing auth: {e}")
            print("Please re-authenticate.")

    print("Please authenticate with your Audible account.")
    print("You will need to provide:")
    print("  - Your Audible email/username")
    print("  - Your password")
    print("  - Your marketplace locale (e.g., 'US', 'UK', 'DE', 'FR')")

    email = input("\nEmail: ")
    password = getpass("Password: ")
    marketplace = input(
        "Marketplace locale (default: US): "
    ).strip().upper() or "US"

    try:
        authenticator = audible.Authenticator.from_login(
            username=email,
            password=password,
            locale=marketplace
        )

        auth_path.parent.mkdir(parents=True, exist_ok=True)
        authenticator.to_file(str(auth_path))
        print("Authentication successful!")
        audible_client = audible.Client(auth=authenticator)
        return authenticator, audible_client

    except (OSError, ValueError, KeyError) as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    auth, client = authenticate()
    app = AudituiApp()
    app.auth = auth
    app.client = client
    app.run()
