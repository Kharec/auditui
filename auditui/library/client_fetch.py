"""Library page fetching helpers for the Audible API client."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from typing import Any

from ..types import LibraryItem, StatusCallback


class LibraryClientFetchMixin:
    """Fetches all library items from paginated Audible endpoints."""

    client: Any

    def fetch_all_items(
        self, on_progress: StatusCallback | None = None
    ) -> list[LibraryItem]:
        """Fetch all library items from the API."""
        response_groups = (
            "contributors,media,product_attrs,product_desc,product_details,"
            "is_finished,listening_status,percent_complete"
        )
        return self._fetch_all_pages(response_groups, on_progress)

    def _fetch_page(
        self,
        page: int,
        page_size: int,
        response_groups: str,
    ) -> tuple[int, list[LibraryItem]]:
        """Fetch one library page and return its index with items."""
        library = self.client.get(
            path="library",
            num_results=page_size,
            page=page,
            response_groups=response_groups,
        )
        items = library.get("items", [])
        return page, list(items)

    def _fetch_all_pages(
        self,
        response_groups: str,
        on_progress: StatusCallback | None = None,
    ) -> list[LibraryItem]:
        """Fetch all library pages using parallel requests after page one."""
        library_response = None
        page_size = 200

        for attempt_size in [200, 100, 50]:
            try:
                library_response = self.client.get(
                    path="library",
                    num_results=attempt_size,
                    page=1,
                    response_groups=response_groups,
                )
                page_size = attempt_size
                break
            except Exception:
                continue

        if not library_response:
            return []

        first_page_items = library_response.get("items", [])
        if not first_page_items:
            return []

        all_items: list[LibraryItem] = list(first_page_items)
        if on_progress:
            on_progress(f"Fetched page 1 ({len(first_page_items)} items)...")

        if len(first_page_items) < page_size:
            return all_items

        total_items_estimate = library_response.get(
            "total_results"
        ) or library_response.get("total")
        if total_items_estimate:
            estimated_pages = (total_items_estimate + page_size - 1) // page_size
            estimated_pages = min(estimated_pages, 1000)
        else:
            estimated_pages = 500

        max_workers = 50
        page_results: dict[int, list[LibraryItem]] = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_page: dict = {}

            for page in range(2, estimated_pages + 1):
                future = executor.submit(
                    self._fetch_page, page, page_size, response_groups
                )
                future_to_page[future] = page

            completed_count = 0
            total_items = len(first_page_items)

            for future in as_completed(future_to_page):
                try:
                    fetched_page, items = future.result()
                    future_to_page.pop(future, None)
                    if not items or len(items) < page_size:
                        for remaining_future in list(future_to_page.keys()):
                            remaining_future.cancel()
                        break

                    page_results[fetched_page] = items
                    total_items += len(items)
                    completed_count += 1
                    if on_progress and completed_count % 20 == 0:
                        on_progress(
                            f"Fetched {completed_count} pages ({total_items} items)..."
                        )

                except Exception:
                    future_to_page.pop(future, None)
                    pass

        for page_num in sorted(page_results.keys()):
            all_items.extend(page_results[page_num])

        return all_items
