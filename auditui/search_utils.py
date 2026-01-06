"""Search helpers for filtering library items."""

from __future__ import annotations

from typing import Callable

from .library import LibraryClient


def build_search_text(item: dict, library_client: LibraryClient | None) -> str:
    """Build a lowercase search string for an item."""
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
    items: list[dict],
    filter_text: str,
    get_search_text: Callable[[dict], str],
) -> list[dict]:
    """Filter items by a search string."""
    if not filter_text:
        return items
    filter_lower = filter_text.lower()
    return [item for item in items if filter_lower in get_search_text(item)]
