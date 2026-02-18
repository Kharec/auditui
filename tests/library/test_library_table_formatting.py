from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from auditui.constants import AUTHOR_NAME_MAX_LENGTH
from auditui.library import (
    create_progress_sort_key,
    create_title_sort_key,
    filter_unfinished_items,
    format_item_as_row,
    truncate_author_name,
)


class StubLibrary:
    """Library facade exposing only helpers needed by table formatting code."""

    def extract_title(self, item: dict) -> str:
        """Return synthetic title value."""
        return item.get("title", "")

    def extract_authors(self, item: dict) -> str:
        """Return synthetic authors value."""
        return item.get("authors", "")

    def extract_runtime_minutes(self, item: dict) -> int | None:
        """Return synthetic minute duration."""
        return item.get("minutes")

    def format_duration(
        self, value: int | None, unit: str = "minutes", default_none: str | None = None
    ) -> str | None:
        """Render runtime in compact minute format for tests."""
        del unit
        return default_none if value is None else f"{value}m"

    def extract_progress_info(self, item: dict) -> float | None:
        """Return synthetic progress percentage value."""
        return item.get("percent")

    def extract_asin(self, item: dict) -> str | None:
        """Return synthetic ASIN value."""
        return item.get("asin")

    def is_finished(self, item: dict) -> bool:
        """Return synthetic finished flag from the item."""
        return bool(item.get("finished"))


@dataclass(slots=True)
class StubDownloads:
    """Download cache adapter exposing just is_cached."""

    cached: set[str]

    def is_cached(self, asin: str) -> bool:
        """Return whether an ASIN is cached."""
        return asin in self.cached


def test_create_title_sort_key_normalizes_accents() -> None:
    """Ensure title sorting removes accents before case-fold compare."""
    key_fn, _ = create_title_sort_key()
    assert key_fn(["Ecole"]) == key_fn(["École"])


def test_create_progress_sort_key_parses_percent_strings() -> None:
    """Ensure progress sorting converts percentages and handles invalid values."""
    key_fn, _ = create_progress_sort_key()
    assert key_fn(["0", "0", "0", "42.5%", ""]) == 42.5
    assert key_fn(["0", "0", "0", "bad", ""]) == 0.0


def test_truncate_author_name_clamps_long_values() -> None:
    """Ensure very long author strings are shortened with ellipsis."""
    long_name = "A" * (AUTHOR_NAME_MAX_LENGTH + 5)
    out = truncate_author_name(long_name)
    assert out.endswith("...")
    assert len(out) <= AUTHOR_NAME_MAX_LENGTH


def test_format_item_as_row_marks_downloaded_titles() -> None:
    """Ensure downloaded ASINs are shown with a checkmark in table rows."""
    item = {
        "title": "Title",
        "authors": "Author",
        "minutes": 90,
        "percent": 12.34,
        "asin": "A1",
    }
    row = format_item_as_row(item, StubLibrary(), cast(Any, StubDownloads({"A1"})))
    assert row == ("Title", "Author", "90m", "12.3%", "✓")


def test_filter_unfinished_items_keeps_only_incomplete() -> None:
    """Ensure unfinished filter excludes items marked as finished."""
    items = [{"id": 1, "finished": False}, {"id": 2, "finished": True}]
    assert filter_unfinished_items(items, StubLibrary()) == [items[0]]
