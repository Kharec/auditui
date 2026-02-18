"""Text search over library items for the filter feature."""

from __future__ import annotations

from typing import Callable

from ..types import LibraryItem

from .client import LibraryClient


def build_search_text(item: LibraryItem, library_client: LibraryClient | None) -> str:
    """Build a single lowercase string from title and authors for matching."""
    if library_client:
        title = library_client.extract_title(item)
        authors = library_client.extract_authors(item)
    else:
        title = item.get("title", "")
        authors = ", ".join(
            a.get("name", "")
            for a in item.get("authors", [])
            if isinstance(a, dict) and a.get("name")
        )
    return f"{title} {authors}".lower()


def filter_items(
    items: list[LibraryItem],
    filter_text: str,
    get_search_text: Callable[[LibraryItem], str],
) -> list[LibraryItem]:
    """Return items whose search text contains filter_text (case-insensitive)."""
    if not filter_text:
        return items
    filter_lower = filter_text.lower()
    return [item for item in items if filter_lower in get_search_text(item)]
