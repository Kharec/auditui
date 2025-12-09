"""Textual application for the Audible TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import App, ComposeResult
from textual.events import Key
from textual.widgets import DataTable, Footer, Header, ProgressBar, Static
from textual.worker import get_current_worker

from .constants import TABLE_COLUMNS, TABLE_CSS
from .downloads import DownloadManager
from .library import LibraryClient
from .playback import PlaybackController

if TYPE_CHECKING:
    from textual.widgets._data_table import ColumnKey


class Auditui(App):
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

    CSS = TABLE_CSS

    def __init__(self, auth=None, client=None) -> None:
        super().__init__()
        self.auth = auth
        self.client = client
        self.library_client = LibraryClient(client) if client else None
        self.download_manager = (
            DownloadManager(auth, client) if auth and client else None
        )
        self.playback = PlaybackController(self.update_status)

        self.all_items: list[dict] = []
        self.current_items: list[dict] = []
        self.show_all_mode = False
        self.progress_sort_reverse = False
        self.title_column_key: ColumnKey | None = None
        self.progress_column_key: ColumnKey | None = None
        self.progress_column_index = 3

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Loading...", id="status")
        table: DataTable = DataTable()
        table.zebra_stripes = True
        table.cursor_type = "row"
        yield table
        yield Static("", id="progress_info")
        yield ProgressBar(id="progress_bar", show_eta=False, show_percentage=False, total=100)
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the table and start fetching library data."""
        table = self.query_one(DataTable)
        table.add_columns(*TABLE_COLUMNS)
        column_keys = list(table.columns.keys())
        self.title_column_key = column_keys[0]
        self.progress_column_key = column_keys[3]

        if self.client:
            self.update_status("Fetching library...")
            self.fetch_library()
        else:
            self.update_status(
                "Not authenticated. Please restart and authenticate.")

        self.set_interval(1.0, self._check_playback_status)
        self.set_interval(0.5, self._update_progress)

    def on_unmount(self) -> None:
        """Clean up on app exit."""
        self.playback.stop()

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

    def _thread_status_update(self, message: str) -> None:
        """Safely update status from worker threads."""
        self.call_from_thread(self.update_status, message)

    @work(exclusive=True, thread=True)
    def fetch_library(self) -> None:
        """Fetch all library items from Audible API in background thread."""
        worker = get_current_worker()
        if worker.is_cancelled or not self.library_client:
            return

        try:
            all_items = self.library_client.fetch_all_items(
                self._thread_status_update)
            self.call_from_thread(self.on_library_loaded, all_items)
        except (OSError, ValueError, KeyError) as exc:
            self.call_from_thread(self.on_library_error, str(exc))

    def on_library_loaded(self, items: list) -> None:
        """Handle successful library load."""
        self.all_items = items
        self.update_status(f"Loaded {len(items)} books")
        self.show_unfinished()

    def on_library_error(self, error: str) -> None:
        """Handle library fetch error."""
        self.update_status(f"Error fetching library: {error}")

    def _populate_table(self, items: list) -> None:
        """Populate the DataTable with library items."""
        table = self.query_one(DataTable)
        table.clear()

        if not items or not self.library_client:
            self.update_status("No books found.")
            return

        for item in items:
            title = self.library_client.extract_title(item)
            author_names = self.library_client.extract_authors(item)
            if author_names and len(author_names) > 40:
                author_names = f"{author_names[:37]}..."
            minutes = self.library_client.extract_runtime_minutes(item)
            runtime_str = self.library_client.format_duration(
                minutes, unit="minutes", default_none="Unknown length"
            )
            percent_complete = self.library_client.extract_progress_info(item)
            progress_str = f"{percent_complete:.1f}%" if percent_complete and percent_complete > 0 else "0%"

            table.add_row(
                title,
                author_names or "Unknown",
                runtime_str or "Unknown",
                progress_str,
                key=title,
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
        if not self.all_items or not self.library_client:
            return

        self.show_all_mode = False
        unfinished_items = [
            item for item in self.all_items if not self.library_client.is_finished(item)
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
        if table.row_count > 0 and self.title_column_key:
            table.sort(self.title_column_key)

    def action_reverse_sort(self) -> None:
        """Sort table by title in descending order."""
        table = self.query_one(DataTable)
        if table.row_count > 0 and self.title_column_key:
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
        """Show all books."""
        self.show_all()

    def action_show_unfinished(self) -> None:
        """Show unfinished books."""
        self.show_unfinished()

    def action_play_selected(self) -> None:
        """Start playing the selected book."""
        if not self.download_manager:
            self.update_status(
                "Not authenticated. Please restart and authenticate.")
            return

        table = self.query_one(DataTable)
        if table.row_count == 0:
            self.update_status("No books available")
            return

        cursor_row = table.cursor_row
        if cursor_row >= len(self.current_items):
            self.update_status("Invalid selection")
            return

        selected_item = self.current_items[cursor_row]
        asin = self.library_client.extract_asin(
            selected_item) if self.library_client else None

        if not asin:
            self.update_status("Could not get ASIN for selected book")
            return

        self._start_playback_async(asin)

    def action_toggle_playback(self) -> None:
        """Toggle pause/resume state."""
        if not self.playback.toggle_playback():
            self.update_status(
                "No playback active. Press Enter to play a book.")

    def _check_playback_status(self) -> None:
        """Check if playback process has finished and update state accordingly."""
        message = self.playback.check_status()
        if message:
            self.update_status(message)
            self._hide_progress()

    def _update_progress(self) -> None:
        """Update the progress bar and info during playback."""
        progress_data = self.playback.get_current_progress()
        if not progress_data or not self.playback.is_playing:
            self._hide_progress()
            return

        chapter_name, chapter_elapsed, chapter_total = progress_data
        if chapter_total <= 0:
            self._hide_progress()
            return

        progress_info = self.query_one("#progress_info", Static)
        progress_bar = self.query_one("#progress_bar", ProgressBar)

        progress_percent = min(
            100.0, (chapter_elapsed / chapter_total) * 100.0)
        progress_bar.update(progress=progress_percent)
        chapter_elapsed_str = self._format_time(chapter_elapsed)
        chapter_total_str = self._format_time(chapter_total)
        progress_info.update(
            f"{chapter_name} | {chapter_elapsed_str} / {chapter_total_str}")
        progress_info.display = True
        progress_bar.display = True

    def _hide_progress(self) -> None:
        """Hide the progress widget."""
        progress_info = self.query_one("#progress_info", Static)
        progress_bar = self.query_one("#progress_bar", ProgressBar)
        progress_info.display = False
        progress_bar.display = False

    def _format_time(self, seconds: float) -> str:
        """Format seconds as HH:MM:SS or MM:SS."""
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @work(exclusive=True, thread=True)
    def _start_playback_async(self, asin: str) -> None:
        """Start playback asynchronously."""
        if not self.download_manager:
            return
        self.playback.prepare_and_start(
            self.download_manager,
            asin,
            self._thread_status_update,
        )
