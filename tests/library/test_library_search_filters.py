from __future__ import annotations

from auditui.library import build_search_text, filter_items


class SearchLibrary:
    """Simple search extraction adapter for build_search_text tests."""

    def extract_title(self, item: dict) -> str:
        """Return a title value from a synthetic item."""
        return item.get("t", "")

    def extract_authors(self, item: dict) -> str:
        """Return an author value from a synthetic item."""
        return item.get("a", "")


def test_build_search_text_uses_library_client_when_present() -> None:
    """Ensure search text delegates to library extractor methods."""
    item = {"t": "The Book", "a": "The Author"}
    assert build_search_text(item, SearchLibrary()) == "the book the author"


def test_filter_items_returns_input_when_filter_empty() -> None:
    """Ensure empty filter bypasses per-item search callback evaluation."""
    items = [{"k": 1}, {"k": 2}]
    assert filter_items(items, "", lambda _item: "ignored") == items


def test_filter_items_matches_case_insensitively() -> None:
    """Ensure search matching is case-insensitive across computed text."""
    items = [{"name": "Alpha"}, {"name": "Beta"}]
    result = filter_items(items, "BETA", lambda item: item["name"].lower())
    assert result == [items[1]]
