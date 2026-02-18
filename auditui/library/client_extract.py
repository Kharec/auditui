"""Metadata extraction helpers for library items."""

from __future__ import annotations

from ..types import LibraryItem


class LibraryClientExtractMixin:
    """Extracts display and status fields from library items."""

    def extract_title(self, item: LibraryItem) -> str:
        """Return the book title from a library item."""
        product = item.get("product", {})
        return (
            product.get("title")
            or item.get("title")
            or product.get("asin", "Unknown Title")
        )

    def extract_authors(self, item: LibraryItem) -> str:
        """Return comma-separated author names from a library item."""
        product = item.get("product", {})
        authors = product.get("authors") or product.get("contributors") or []
        if not authors and "authors" in item:
            authors = item.get("authors", [])
        author_names = [
            author.get("name", "") for author in authors if isinstance(author, dict)
        ]
        return ", ".join(author_names) or "Unknown"

    def extract_runtime_minutes(self, item: LibraryItem) -> int | None:
        """Return runtime in minutes if present."""
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

    def extract_progress_info(self, item: LibraryItem) -> float | None:
        """Return progress percentage (0-100) if present."""
        percent_complete = item.get("percent_complete")
        listening_status = item.get("listening_status", {})
        if isinstance(listening_status, dict) and percent_complete is None:
            percent_complete = listening_status.get("percent_complete")
        return float(percent_complete) if percent_complete is not None else None

    def extract_asin(self, item: LibraryItem) -> str | None:
        """Return the ASIN for a library item."""
        product = item.get("product", {})
        return item.get("asin") or product.get("asin")

    def is_finished(self, item: LibraryItem) -> bool:
        """Return True if the item is marked or inferred as finished."""
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
            isinstance(percent_complete, (int, float)) and percent_complete >= 100
        )
