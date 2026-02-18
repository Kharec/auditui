"""Playback key handling, progress bar updates, and position save."""

from __future__ import annotations

from textual.containers import Horizontal
from textual.events import Key
from textual.widgets import DataTable, ProgressBar, Static

from ..library import LibraryClient


class AppProgressMixin:
    def on_key(self, event: Key) -> None:
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

    def _check_playback_status(self) -> None:
        message = self.playback.check_status()
        if message:
            self.update_status(message)
            self._hide_progress()

    def _update_progress(self) -> None:
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
        progress_bar_container = self.query_one(
            "#progress_bar_container", Horizontal)

        progress_percent = min(
            100.0, max(0.0, (chapter_elapsed / chapter_total) * 100.0)
        )
        progress_bar.update(progress=progress_percent)
        chapter_elapsed_str = LibraryClient.format_time(chapter_elapsed)
        chapter_total_str = LibraryClient.format_time(chapter_total)
        progress_info.update(
            f"{chapter_name} | {chapter_elapsed_str} / {chapter_total_str}"
        )
        progress_info.display = True
        progress_bar_container.display = True

    def _hide_progress(self) -> None:
        progress_info = self.query_one("#progress_info", Static)
        progress_bar_container = self.query_one(
            "#progress_bar_container", Horizontal)
        progress_info.display = False
        progress_bar_container.display = False

    def _save_position_periodically(self) -> None:
        self.playback.update_position_if_needed()
