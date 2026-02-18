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
        response_groups = "contributors,product_attrs,product_desc,is_finished,listening_status,percent_complete"
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

        estimated_pages = self._estimate_total_pages(library_response, page_size)
        page_results = self._fetch_remaining_pages(
            response_groups=response_groups,
            page_size=page_size,
            estimated_pages=estimated_pages,
            initial_total=len(first_page_items),
            on_progress=on_progress,
        )

        for page_num in sorted(page_results.keys()):
            all_items.extend(page_results[page_num])

        return all_items

    def _estimate_total_pages(self, library_response: dict, page_size: int) -> int:
        """Estimate total pages from API metadata with a conservative cap."""
        total_items_estimate = library_response.get(
            "total_results"
        ) or library_response.get("total")
        if not total_items_estimate:
            return 500
        estimated_pages = (total_items_estimate + page_size - 1) // page_size
        return min(estimated_pages, 1000)

    def _fetch_remaining_pages(
        self,
        response_groups: str,
        page_size: int,
        estimated_pages: int,
        initial_total: int,
        on_progress: StatusCallback | None = None,
    ) -> dict[int, list[LibraryItem]]:
        """Fetch pages 2..N with bounded in-flight requests for faster startup."""
        page_results: dict[int, list[LibraryItem]] = {}
        max_workers = min(16, max(1, estimated_pages - 1))
        next_page_to_submit = 2
        stop_page = estimated_pages + 1
        completed_count = 0
        total_items = initial_total

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_page: dict = {}

            while (
                next_page_to_submit <= estimated_pages
                and next_page_to_submit < stop_page
                and len(future_to_page) < max_workers
            ):
                future = executor.submit(
                    self._fetch_page,
                    next_page_to_submit,
                    page_size,
                    response_groups,
                )
                future_to_page[future] = next_page_to_submit
                next_page_to_submit += 1

            while future_to_page:
                future = next(as_completed(future_to_page))
                page_num = future_to_page.pop(future)
                try:
                    fetched_page, items = future.result()
                except Exception:
                    continue

                if items:
                    page_results[fetched_page] = items
                    total_items += len(items)
                    completed_count += 1
                    if on_progress and completed_count % 20 == 0:
                        on_progress(
                            f"Fetched {completed_count} pages ({total_items} items)..."
                        )
                if len(items) < page_size:
                    stop_page = min(stop_page, fetched_page)

                while (
                    next_page_to_submit <= estimated_pages
                    and next_page_to_submit < stop_page
                    and len(future_to_page) < max_workers
                ):
                    next_future = executor.submit(
                        self._fetch_page,
                        next_page_to_submit,
                        page_size,
                        response_groups,
                    )
                    future_to_page[next_future] = next_page_to_submit
                    next_page_to_submit += 1

        return page_results
