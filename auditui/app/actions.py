"""Selection, playback/download/finish actions, modals, and filter."""

from __future__ import annotations

from textual import work
from textual.widgets import DataTable

from ..constants import SEEK_SECONDS
from ..ui import FilterScreen, HelpScreen, StatsScreen


class AppActionsMixin:
    def _get_selected_asin(self) -> str | None:
        if not self.download_manager:
            self.update_status(
                "Not authenticated. Please restart and authenticate.")
            return None
        table = self.query_one("#library_table", DataTable)
        if table.row_count == 0:
            self.update_status("No books available")
            return None
        cursor_row = table.cursor_row
        if cursor_row >= len(self.current_items):
            self.update_status("Invalid selection")
            return None
        if not self.library_client:
            self.update_status("Library client not available")
            return None
        selected_item = self.current_items[cursor_row]
        asin = self.library_client.extract_asin(selected_item)
        if not asin:
            self.update_status("Could not get ASIN for selected book")
            return None
        return asin

    def action_play_selected(self) -> None:
        asin = self._get_selected_asin()
        if asin:
            self._start_playback_async(asin)

    def action_toggle_playback(self) -> None:
        if not self.playback.toggle_playback():
            self._no_playback_message()

    def action_seek_forward(self) -> None:
        if not self.playback.seek_forward(SEEK_SECONDS):
            self._no_playback_message()

    def action_seek_backward(self) -> None:
        if not self.playback.seek_backward(SEEK_SECONDS):
            self._no_playback_message()

    def action_next_chapter(self) -> None:
        if not self.playback.seek_to_next_chapter():
            self._no_playback_message()

    def action_previous_chapter(self) -> None:
        if not self.playback.seek_to_previous_chapter():
            self._no_playback_message()

    def action_increase_speed(self) -> None:
        if not self.playback.increase_speed():
            self._no_playback_message()

    def action_decrease_speed(self) -> None:
        if not self.playback.decrease_speed():
            self._no_playback_message()

    def action_toggle_finished(self) -> None:
        asin = self._get_selected_asin()
        if asin:
            self._toggle_finished_async(asin)

    @work(exclusive=True, thread=True)
    def _toggle_finished_async(self, asin: str) -> None:
        if not self.library_client:
            return

        selected_item = None
        for item in self.current_items:
            if self.library_client.extract_asin(item) == asin:
                selected_item = item
                break

        if not selected_item:
            return

        if self.library_client.is_finished(selected_item):
            self.call_from_thread(self.update_status,
                                  "Already marked as finished")
            return

        success = self.library_client.mark_as_finished(asin, selected_item)
        message = "Marked as finished" if success else "Failed to mark as finished"

        self.call_from_thread(self.update_status, message)
        if success:
            if self.download_manager and self.download_manager.is_cached(asin):
                self.download_manager.remove_cached(
                    asin, notify=self._thread_status_update
                )
            self.call_from_thread(self.fetch_library)

    def _no_playback_message(self) -> None:
        self.update_status("No playback active. Press Enter to play a book.")

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_show_stats(self) -> None:
        self.push_screen(StatsScreen())

    def action_filter(self) -> None:
        self.push_screen(
            FilterScreen(
                self.filter_text,
                on_change=self._apply_filter,
            ),
            self._apply_filter,
        )

    def action_clear_filter(self) -> None:
        if self.filter_text:
            self.filter_text = ""
            self._refresh_filtered_view()
            self.update_status("Filter cleared")

    def _apply_filter(self, filter_text: str | None) -> None:
        self.filter_text = filter_text or ""
        self._refresh_filtered_view()

    def action_toggle_download(self) -> None:
        asin = self._get_selected_asin()
        if asin:
            self._toggle_download_async(asin)

    @work(exclusive=True, thread=True)
    def _toggle_download_async(self, asin: str) -> None:
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
        if not self.download_manager:
            return
        self.playback.prepare_and_start(
            self.download_manager,
            asin,
            self._thread_status_update,
        )
