from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from auditui.app import Auditui
from auditui.library import build_search_text, filter_items


class StubLibrary:
    """Minimal library facade used by search-related app helpers."""

    def extract_title(self, item: dict) -> str:
        """Return title from a synthetic item."""
        return item.get("title", "")

    def extract_authors(self, item: dict) -> str:
        """Return authors from a synthetic item."""
        return item.get("authors", "")


@dataclass(slots=True)
class DummyAuditui:
    """Narrow object compatible with Auditui search-cache helper calls."""

    _search_text_cache: dict[int, str] = field(default_factory=dict)
    library_client: StubLibrary = field(default_factory=StubLibrary)


def test_get_search_text_is_cached() -> None:
    """Ensure repeated text extraction for one item reuses cache entries."""
    item = {"title": "Title", "authors": "Author"}
    dummy = DummyAuditui()
    first = Auditui._get_search_text(cast(Auditui, dummy), item)
    second = Auditui._get_search_text(cast(Auditui, dummy), item)
    assert first == "title author"
    assert first == second
    assert len(dummy._search_text_cache) == 1


def test_filter_items_uses_cached_callable() -> None:
    """Ensure filter_items cooperates with a memoized search text callback."""
    library = StubLibrary()
    cache: dict[int, str] = {}
    items = [
        {"title": "Alpha", "authors": "Author One"},
        {"title": "Beta", "authors": "Author Two"},
    ]

    def cached(item: dict) -> str:
        """Build and cache normalized search text per object identity."""
        cache_key = id(item)
        if cache_key not in cache:
            cache[cache_key] = build_search_text(item, cast(Any, library))
        return cache[cache_key]

    result = filter_items(items, "beta", cached)
    assert result == [items[1]]


def test_build_search_text_without_library_client() -> None:
    """Ensure fallback search text path handles inline author dicts."""
    item = {"title": "Title", "authors": [{"name": "A"}, {"name": "B"}]}
    assert build_search_text(item, None) == "title a, b"
