"""Table population, sorting, filter view, and search cache."""

from __future__ import annotations

from ..library import (
    filter_items,
    filter_unfinished_items,
    format_item_as_row,
    create_progress_sort_key,
    create_title_sort_key,
)
from ..types import LibraryItem
from textual.widgets import DataTable, Static


class AppTableMixin:
    def _populate_table(self, items: list[LibraryItem]) -> None:
        table = self.query_one(DataTable)
        table.clear()

        if not items or not self.library_client:
            self.update_status("No books found.")
            return

        for item in items:
            title, author, runtime, progress, downloaded = format_item_as_row(
                item, self.library_client, self.download_manager
            )
            table.add_row(title, author, runtime,
                          progress, downloaded, key=title)

        self.current_items = items
        status = self.query_one("#status", Static)
        status.display = False
        self._apply_column_widths(table)

    def _refresh_table(self) -> None:
        if self.current_items:
            self._populate_table(self.current_items)

    def show_all(self) -> None:
        if not self.all_items:
            return
        self.show_all_mode = True
        self._refresh_filtered_view()

    def show_unfinished(self) -> None:
        if not self.all_items or not self.library_client:
            return
        self.show_all_mode = False
        self._refresh_filtered_view()

    def action_sort(self) -> None:
        table = self.query_one(DataTable)
        if table.row_count > 0 and self.title_column_key:
            title_key, reverse = create_title_sort_key(self.title_sort_reverse)
            table.sort(key=title_key, reverse=reverse)
            self.title_sort_reverse = not self.title_sort_reverse

    def action_sort_by_progress(self) -> None:
        table = self.query_one(DataTable)
        if table.row_count > 0:
            self.progress_sort_reverse = not self.progress_sort_reverse
            progress_key, reverse = create_progress_sort_key(
                self.progress_column_index, self.progress_sort_reverse
            )
            table.sort(key=progress_key, reverse=reverse)

    def action_show_all(self) -> None:
        if self.show_all_mode:
            self.show_unfinished()
        else:
            self.show_all()

    def _refresh_filtered_view(self) -> None:
        if not self.all_items:
            return

        items = self.all_items

        if self.filter_text:
            items = filter_items(items, self.filter_text,
                                 self._get_search_text)
            self._populate_table(items)
            self.update_status(
                f"Filter: '{self.filter_text}' ({len(items)} books)")
            return

        if not self.show_all_mode and self.library_client:
            items = filter_unfinished_items(items, self.library_client)

        self._populate_table(items)

    def _get_search_text(self, item: LibraryItem) -> str:
        cache_key = id(item)
        cached = self._search_text_cache.get(cache_key)
        if cached is not None:
            return cached
        from ..library import build_search_text
        search_text = build_search_text(item, self.library_client)
        self._search_text_cache[cache_key] = search_text
        return search_text

    def _prime_search_cache(self, items: list[LibraryItem]) -> None:
        for item in items:
            self._get_search_text(item)
