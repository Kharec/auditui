from __future__ import annotations

from auditui.app import Auditui
from auditui.search_utils import build_search_text, filter_items


class StubLibrary:
    def extract_title(self, item: dict) -> str:
        return item.get("title", "")

    def extract_authors(self, item: dict) -> str:
        return item.get("authors", "")


def test_get_search_text_is_cached() -> None:
    class Dummy:
        def __init__(self) -> None:
            self._search_text_cache: dict[int, str] = {}
            self.library_client = StubLibrary()

    item = {"title": "Title", "authors": "Author"}
    dummy = Dummy()
    first = Auditui._get_search_text(dummy, item)
    second = Auditui._get_search_text(dummy, item)
    assert first == "title author"
    assert first == second
    assert len(dummy._search_text_cache) == 1


def test_filter_items_uses_cache() -> None:
    library = StubLibrary()
    cache: dict[int, str] = {}
    items = [
        {"title": "Alpha", "authors": "Author One"},
        {"title": "Beta", "authors": "Author Two"},
    ]

    def cached(item: dict) -> str:
        cache_key = id(item)
        if cache_key not in cache:
            cache[cache_key] = build_search_text(item, library)
        return cache[cache_key]

    result = filter_items(items, "beta", cached)
    assert result == [items[1]]


def test_build_search_text_without_library() -> None:
    item = {"title": "Title", "authors": [{"name": "A"}, {"name": "B"}]}
    assert build_search_text(item, None) == "title a, b"
