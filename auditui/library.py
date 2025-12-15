"""Library helpers for fetching and formatting Audible data."""

from typing import Callable, List

import audible


ProgressCallback = Callable[[str], None]


class LibraryClient:
    """Helper for interacting with the Audible library."""

    def __init__(self, client: audible.Client) -> None:
        self.client = client

    def fetch_all_items(self, on_progress: ProgressCallback | None = None) -> list:
        """Fetch all library items from the API."""
        response_groups = (
            "contributors,media,product_attrs,product_desc,product_details,"
            "rating,is_finished,listening_status,percent_complete"
        )
        return self._fetch_all_pages(response_groups, on_progress)

    def _fetch_all_pages(
        self, response_groups: str, on_progress: ProgressCallback | None = None
    ) -> list:
        """Fetch all pages of library items from the API."""
        all_items: List[dict] = []
        page = 1
        page_size = 50

        while True:
            library = self.client.get(
                path="library",
                num_results=page_size,
                page=page,
                response_groups=response_groups,
            )

            items = list(library.get("items", []))
            if not items:
                break

            all_items.extend(items)
            if on_progress:
                on_progress(f"Fetched page {page} ({len(items)} items)...")

            if len(items) < page_size:
                break

            page += 1

        return all_items

    def extract_title(self, item: dict) -> str:
        """Extract title from library item."""
        product = item.get("product", {})
        return (
            product.get("title")
            or item.get("title")
            or product.get("asin", "Unknown Title")
        )

    def extract_authors(self, item: dict) -> str:
        """Extract author names from library item."""
        product = item.get("product", {})
        authors = product.get("authors") or product.get("contributors") or []
        if not authors and "authors" in item:
            authors = item.get("authors", [])

        author_names = [a.get("name", "")
                        for a in authors if isinstance(a, dict)]
        return ", ".join(author_names) or "Unknown"

    def extract_runtime_minutes(self, item: dict) -> int | None:
        """Extract runtime in minutes from library item."""
        product = item.get("product", {})
        runtime_fields = [
            "runtime_length_min",
            "runtime_length",
            "vLength",
            "length",
            "duration",
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
        if isinstance(runtime, (int, float)):
            return int(runtime)
        return None

    def extract_progress_info(self, item: dict) -> float | None:
        """Extract progress percentage from library item."""
        percent_complete = item.get("percent_complete")
        listening_status = item.get("listening_status", {})

        if isinstance(listening_status, dict) and percent_complete is None:
            percent_complete = listening_status.get("percent_complete")

        return float(percent_complete) if percent_complete is not None else None

    def extract_asin(self, item: dict) -> str | None:
        """Extract ASIN from library item."""
        product = item.get("product", {})
        return item.get("asin") or product.get("asin")

    def is_finished(self, item: dict) -> bool:
        """Check if a library item is finished."""
        is_finished_flag = item.get("is_finished")
        percent_complete = item.get("percent_complete")
        listening_status = item.get("listening_status")

        if isinstance(listening_status, dict):
            is_finished_flag = is_finished_flag or listening_status.get(
                "is_finished", False
            )
            if percent_complete is None:
                percent_complete = listening_status.get("percent_complete", 0)

        return bool(is_finished_flag) or (
            isinstance(percent_complete, (int, float)
                       ) and percent_complete >= 100
        )

    def get_last_position(self, asin: str) -> float | None:
        """Get the last playback position for a book in seconds."""
        try:
            response = self.client.get(
                path="1.0/annotations/lastpositions",
                asins=asin,
            )
            annotations = response.get("asin_last_position_heard_annots", [])

            for annot in annotations:
                if annot.get("asin") != asin:
                    continue

                last_position_heard = annot.get("last_position_heard", {})
                if not isinstance(last_position_heard, dict):
                    continue

                if last_position_heard.get("status") == "DoesNotExist":
                    return None

                position_ms = last_position_heard.get("position_ms")
                if position_ms is not None:
                    return float(position_ms) / 1000.0

            return None
        except (OSError, ValueError, KeyError):
            return None

    def _get_content_reference(self, asin: str) -> dict | None:
        """Get content reference data including ACR and version."""
        try:
            response = self.client.get(
                path=f"1.0/content/{asin}/metadata",
                response_groups="content_reference",
            )
            content_metadata = response.get("content_metadata", {})
            content_reference = content_metadata.get("content_reference", {})
            if isinstance(content_reference, dict):
                return content_reference
            return None
        except (OSError, ValueError, KeyError):
            return None

    def save_last_position(self, asin: str, position_seconds: float) -> bool:
        """Save the last playback position for a book."""
        if position_seconds <= 0:
            return False

        content_ref = self._get_content_reference(asin)
        if not content_ref:
            return False

        acr = content_ref.get("acr")
        if not acr:
            return False

        body = {
            "acr": acr,
            "asin": asin,
            "position_ms": int(position_seconds * 1000),
        }

        if version := content_ref.get("version"):
            body["version"] = version

        try:
            self.client.put(
                path=f"1.0/lastpositions/{asin}",
                body=body,
            )
            return True
        except (OSError, ValueError, KeyError):
            return False

    @staticmethod
    def format_duration(
        value: int | None, unit: str = "minutes", default_none: str | None = None
    ) -> str | None:
        """Format duration value into a human-readable string."""
        if value is None or value <= 0:
            return default_none

        total_minutes = int(value)
        if unit == "seconds":
            total_minutes //= 60

        hours, minutes = divmod(total_minutes, 60)

        parts = []
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

        return " ".join(parts) if parts else default_none

    @staticmethod
    def format_time(seconds: float) -> str:
        """Format seconds as HH:MM:SS or MM:SS."""
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
