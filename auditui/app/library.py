"""Library fetch and load/error handlers."""

from __future__ import annotations

from textual import work
from textual.worker import get_current_worker

from ..types import LibraryItem


class AppLibraryMixin:
    @work(exclusive=True, thread=True)
    def fetch_library(self) -> None:
        worker = get_current_worker()
        if worker.is_cancelled or not self.library_client:
            return

        try:
            all_items = self.library_client.fetch_all_items(
                self._thread_status_update)
            self.call_from_thread(self.on_library_loaded, all_items)
        except (OSError, ValueError, KeyError) as exc:
            self.call_from_thread(self.on_library_error, str(exc))

    def on_library_loaded(self, items: list[LibraryItem]) -> None:
        self.all_items = items
        self._search_text_cache.clear()
        self._prime_search_cache(items)
        self.update_status(f"Loaded {len(items)} books")
        if self.show_all_mode:
            self.show_all()
        else:
            self.show_unfinished()

    def on_library_error(self, error: str) -> None:
        self.update_status(f"Error fetching library: {error}")
