"""Textual application for the Audible TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.events import Key, Resize
from textual.widgets import DataTable, ProgressBar, Static
from textual.worker import get_current_worker

from . import __version__
from .constants import (
    PROGRESS_COLUMN_INDEX,
    SEEK_SECONDS,
    TABLE_COLUMN_DEFS,
    TABLE_CSS,
)
from .downloads import DownloadManager
from .library import LibraryClient
from .playback import PlaybackController
from .table_utils import (
    create_progress_sort_key,
    create_title_sort_key,
    filter_unfinished_items,
    format_item_as_row,
)
from .ui import HelpScreen, StatsScreen

if TYPE_CHECKING:
    from textual.widgets._data_table import ColumnKey


class Auditui(App):
    """Main application class for the Audible TUI app."""

    theme = "textual-dark"
    SHOW_PALETTE = False

    BINDINGS = [
        ("?", "show_help", "Help"),
        ("s", "show_stats", "Stats"),
        ("n", "sort", "Sort by name"),
        ("p", "sort_by_progress", "Sort by progress"),
        ("a", "show_all", "All/Unfinished"),
        ("enter", "play_selected", "Play"),
        ("space", "toggle_playback", "Pause/Resume"),
        ("left", "seek_backward", "-30s"),
        ("right", "seek_forward", "+30s"),
        ("ctrl+left", "previous_chapter", "Previous chapter"),
        ("ctrl+right", "next_chapter", "Next chapter"),
        ("up", "increase_speed", "Increase speed"),
        ("down", "decrease_speed", "Decrease speed"),
        ("f", "toggle_finished", "Mark finished/unfinished"),
        ("d", "toggle_download", "Download/Delete"),
        ("q", "quit", "Quit"),
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
        self.playback = PlaybackController(
            self.update_status, self.library_client)

        self.all_items: list[dict] = []
        self.current_items: list[dict] = []
        self.show_all_mode = False
        self.title_sort_reverse = False
        self.progress_sort_reverse = False
        self.title_column_key: ColumnKey | None = None
        self.progress_column_index = PROGRESS_COLUMN_INDEX

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static("? Help", id="top_left"),
            Static(f"Auditui v{__version__}", id="top_center"),
            Static("q Quit", id="top_right"),
            id="top_bar",
        )
        yield Static("Loading...", id="status")
        table: DataTable = DataTable()
        table.zebra_stripes = True
        table.cursor_type = "row"
        yield table
        yield Static("", id="progress_info")
        yield ProgressBar(id="progress_bar", show_eta=False, show_percentage=False, total=100)

    def on_mount(self) -> None:
        """Initialize the table and start fetching library data."""
        table = self.query_one(DataTable)
        for column_name, _ratio in TABLE_COLUMN_DEFS:
            table.add_column(column_name, width=1)
        self.call_after_refresh(lambda: self._apply_column_widths(table))
        column_keys = list(table.columns.keys())
        self.title_column_key = column_keys[0]

        if self.client:
            self.update_status("Fetching library...")
            self.fetch_library()
        else:
            self.update_status(
                "Not authenticated. Please restart and authenticate.")

        self.set_interval(1.0, self._check_playback_status)
        self.set_interval(0.5, self._update_progress)
        self.set_interval(30.0, self._save_position_periodically)

    def on_unmount(self) -> None:
        """Clean up on app exit."""
        self.playback.stop()
        if self.download_manager:
            self.download_manager.close()

    def on_resize(self, event: Resize) -> None:
        """Keep table columns responsive to terminal width changes."""
        del event
        try:
            table = self.query_one(DataTable)
        except Exception:
            return
        self._apply_column_widths(table)

    def on_key(self, event: Key) -> None:
        """Handle key presses."""
        if self.playback.is_playing:
            if event.key == "ctrl+left":
                event.prevent_default()
                self.action_previous_chapter()
                return
            elif event.key == "ctrl+right":
                event.prevent_default()
                self.action_next_chapter()
                return
            elif event.key == "left":
                event.prevent_default()
                self.action_seek_backward()
                return
            elif event.key == "right":
                event.prevent_default()
                self.action_seek_forward()
                return
            elif event.key == "up":
                event.prevent_default()
                self.action_increase_speed()
                return
            elif event.key == "down":
                event.prevent_default()
                self.action_decrease_speed()
                return

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
        status.display = True
        status.update(message)

    def _apply_column_widths(self, table: DataTable) -> None:
        """Assign proportional column widths based on available space."""
        if not table.columns:
            return

        column_keys = list(table.columns.keys())
        ratios = [ratio for _, ratio in TABLE_COLUMN_DEFS]
        total_ratio = sum(ratios) or len(column_keys)
        content_width = table.scrollable_content_region.width
        available_width = content_width
        if available_width <= 0:
            return

        widths: list[int] = []
        for ratio in ratios:
            width = max(1, (available_width * ratio) // total_ratio)
            widths.append(width)

        remainder = available_width - sum(widths)
        for i in range(remainder):
            widths[i % len(widths)] += 1

        for column_key, width in zip(column_keys, widths):
            column = table.columns[column_key]
            column.auto_width = False
            column.width = width
        table.refresh()

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

    def on_library_loaded(self, items: list[dict]) -> None:
        """Handle successful library load."""
        self.all_items = items
        self.update_status(f"Loaded {len(items)} books")
        self.show_unfinished()

    def on_library_error(self, error: str) -> None:
        """Handle library fetch error."""
        self.update_status(f"Error fetching library: {error}")

    def _populate_table(self, items: list[dict]) -> None:
        """Populate the DataTable with library items."""
        table = self.query_one(DataTable)
        table.clear()

        if not items or not self.library_client:
            self.update_status("No books found.")
            return

        for item in items:
            title, author, runtime, progress, downloaded = format_item_as_row(
                item, self.library_client, self.download_manager)
            table.add_row(title, author, runtime,
                          progress, downloaded, key=title)

        self.current_items = items
        status = self.query_one("#status", Static)
        status.display = False

    def _refresh_table(self) -> None:
        """Refresh the table with current items."""
        if self.current_items:
            self._populate_table(self.current_items)

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
        unfinished_items = filter_unfinished_items(
            self.all_items, self.library_client)
        self._populate_table(unfinished_items)

    def action_sort(self) -> None:
        """Sort table by title, toggling direction on each press."""
        table = self.query_one(DataTable)
        if table.row_count > 0 and self.title_column_key:
            title_key, reverse = create_title_sort_key(self.title_sort_reverse)
            table.sort(key=title_key, reverse=reverse)
            self.title_sort_reverse = not self.title_sort_reverse

    def action_sort_by_progress(self) -> None:
        """Sort table by progress percentage, toggling direction on each press."""
        table = self.query_one(DataTable)
        if table.row_count > 0:
            self.progress_sort_reverse = not self.progress_sort_reverse
            progress_key, reverse = create_progress_sort_key(
                self.progress_column_index, self.progress_sort_reverse)
            table.sort(key=progress_key, reverse=reverse)

    def action_show_all(self) -> None:
        """Toggle between showing all and unfinished books."""
        if self.show_all_mode:
            self.show_unfinished()
        else:
            self.show_all()

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

        if not self.library_client:
            self.update_status("Library client not available")
            return

        selected_item = self.current_items[cursor_row]
        asin = self.library_client.extract_asin(selected_item)

        if not asin:
            self.update_status("Could not get ASIN for selected book")
            return

        self._start_playback_async(asin)

    def action_toggle_playback(self) -> None:
        """Toggle pause/resume state."""
        if not self.playback.toggle_playback():
            self._no_playback_message()

    def action_seek_forward(self) -> None:
        """Seek forward 30 seconds."""
        if not self.playback.seek_forward(SEEK_SECONDS):
            self._no_playback_message()

    def action_seek_backward(self) -> None:
        """Seek backward 30 seconds."""
        if not self.playback.seek_backward(SEEK_SECONDS):
            self._no_playback_message()

    def action_next_chapter(self) -> None:
        """Seek to the next chapter."""
        if not self.playback.seek_to_next_chapter():
            self._no_playback_message()

    def action_previous_chapter(self) -> None:
        """Seek to the previous chapter."""
        if not self.playback.seek_to_previous_chapter():
            self._no_playback_message()

    def action_increase_speed(self) -> None:
        """Increase playback speed."""
        if not self.playback.increase_speed():
            self._no_playback_message()

    def action_decrease_speed(self) -> None:
        """Decrease playback speed."""
        if not self.playback.decrease_speed():
            self._no_playback_message()

    def action_toggle_finished(self) -> None:
        """Toggle finished/unfinished status for the selected book."""
        if not self.library_client:
            self.update_status("Library client not available")
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
        asin = self.library_client.extract_asin(selected_item)

        if not asin:
            self.update_status("Could not get ASIN for selected book")
            return

        self._toggle_finished_async(asin)

    @work(exclusive=True, thread=True)
    def _toggle_finished_async(self, asin: str) -> None:
        """Toggle finished/unfinished status asynchronously."""
        if not self.library_client:
            return

        selected_item = None
        for item in self.current_items:
            if self.library_client.extract_asin(item) == asin:
                selected_item = item
                break

        if not selected_item:
            return

        is_currently_finished = self.library_client.is_finished(selected_item)

        if is_currently_finished:
            success = self.library_client.mark_as_unfinished(asin)
            message = "Marked as unfinished" if success else "Failed to mark as unfinished"
        else:
            success = self.library_client.mark_as_finished(asin, selected_item)
            message = "Marked as finished" if success else "Failed to mark as finished"

        self.call_from_thread(self.update_status, message)
        if success:
            self.call_from_thread(self.fetch_library)

    def _no_playback_message(self) -> None:
        """Show message when no playback is active."""
        self.update_status("No playback active. Press Enter to play a book.")

    def action_show_help(self) -> None:
        """Show the help screen with all keybindings."""
        self.push_screen(HelpScreen())

    def action_show_stats(self) -> None:
        """Show the stats screen with listening statistics."""
        self.push_screen(StatsScreen())

    def _check_playback_status(self) -> None:
        """Check if playback process has finished and update state accordingly."""
        message = self.playback.check_status()
        if message:
            self.update_status(message)
            self._hide_progress()

    def _update_progress(self) -> None:
        """Update the progress bar and info during playback."""
        if not self.playback.is_playing:
            self._hide_progress()
            return

        progress_data = self.playback.get_current_progress()
        if not progress_data:
            self._hide_progress()
            return

        chapter_name, chapter_elapsed, chapter_total = progress_data
        if chapter_total <= 0:
            self._hide_progress()
            return

        progress_info = self.query_one("#progress_info", Static)
        progress_bar = self.query_one("#progress_bar", ProgressBar)

        progress_percent = min(100.0, max(
            0.0, (chapter_elapsed / chapter_total) * 100.0))
        progress_bar.update(progress=progress_percent)
        chapter_elapsed_str = LibraryClient.format_time(chapter_elapsed)
        chapter_total_str = LibraryClient.format_time(chapter_total)
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

    def _save_position_periodically(self) -> None:
        """Periodically save playback position."""
        self.playback.update_position_if_needed()

    def action_toggle_download(self) -> None:
        """Toggle download/remove for the selected book."""
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

        if not self.library_client:
            self.update_status("Library client not available")
            return

        selected_item = self.current_items[cursor_row]
        asin = self.library_client.extract_asin(selected_item)

        if not asin:
            self.update_status("Could not get ASIN for selected book")
            return

        self._toggle_download_async(asin)

    @work(exclusive=True, thread=True)
    def _toggle_download_async(self, asin: str) -> None:
        """Toggle download/remove asynchronously."""
        if not self.download_manager:
            return

        if self.download_manager.is_cached(asin):
            self.download_manager.remove_cached(
                asin, self._thread_status_update)
        else:
            self.download_manager.get_or_download(
                asin, self._thread_status_update)

        self.call_from_thread(self._refresh_table)

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
