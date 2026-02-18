"""Main layout: compose, mount, resize, status bar, table column widths."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.events import Resize
from textual.widgets import DataTable, ProgressBar, Static

from .. import __version__
from ..constants import TABLE_COLUMN_DEFS


class AppLayoutMixin:
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static("? Help", id="top_left"),
            Static(f"Auditui v{__version__}", id="top_center"),
            Static("q Quit", id="top_right"),
            id="top_bar",
        )
        yield Static("Loading...", id="status")
        table = DataTable(id="library_table")
        table.zebra_stripes = True
        table.cursor_type = "row"
        yield table
        yield Static("", id="progress_info")
        with Horizontal(id="progress_bar_container"):
            yield ProgressBar(
                id="progress_bar", show_eta=False, show_percentage=False, total=100
            )

    def on_mount(self) -> None:
        self.theme = "textual-dark"
        self.call_after_refresh(self._init_table_and_intervals)

    def _init_table_and_intervals(self) -> None:
        table = self.query_one("#library_table", DataTable)
        for column_name, _ratio in TABLE_COLUMN_DEFS:
            table.add_column(column_name)
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
        self.playback.stop()
        if self.download_manager:
            self.download_manager.close()

    def on_resize(self, event: Resize) -> None:
        del event
        try:
            table = self.query_one("#library_table", DataTable)
        except Exception:
            return
        self.call_after_refresh(lambda: self._apply_column_widths(table))

    def update_status(self, message: str) -> None:
        status = self.query_one("#status", Static)
        status.display = True
        status.update(message)

    def _apply_column_widths(self, table: DataTable) -> None:
        if not table.columns:
            return

        column_keys = list(table.columns.keys())
        num_cols = len(column_keys)
        ratios = [ratio for _, ratio in TABLE_COLUMN_DEFS]
        total_ratio = sum(ratios) or num_cols

        content_width = table.scrollable_content_region.width
        if content_width <= 0:
            content_width = table.size.width
        if content_width <= 0:
            return

        padding_total = 2 * table.cell_padding * num_cols
        distributable = max(num_cols, content_width - padding_total)

        widths = []
        for ratio in ratios:
            w = max(1, (distributable * ratio) // total_ratio)
            widths.append(w)

        remainder = distributable - sum(widths)
        if remainder > 0:
            indices = sorted(
                range(num_cols), key=lambda i: ratios[i], reverse=True)
            for i in range(remainder):
                widths[indices[i % num_cols]] += 1

        for column_key, w in zip(column_keys, widths):
            col = table.columns[column_key]
            col.auto_width = False
            col.width = w
        table.refresh()

    def _thread_status_update(self, message: str) -> None:
        self.call_from_thread(self.update_status, message)
