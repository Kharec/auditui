from __future__ import annotations

from auditui.app.table import AppTableMixin


class DummyTableApp(AppTableMixin):
    """Minimal host exposing library client for row key helper tests."""

    def __init__(self) -> None:
        """Initialize a fake library client with ASIN extraction."""
        self.library_client = type(
            "Library",
            (),
            {"extract_asin": lambda self, item: item.get("asin")},
        )()


def test_build_row_key_prefers_asin_and_remains_unique() -> None:
    """Ensure duplicate ASINs receive deterministic unique key suffixes."""
    app = DummyTableApp()
    used: set[str] = set()
    item = {"asin": "ASIN1"}
    first = app._build_row_key(item, "Title", 0, used)
    second = app._build_row_key(item, "Title", 1, used)
    assert first == "ASIN1"
    assert second == "ASIN1#2"


def test_build_row_key_falls_back_to_title_and_index() -> None:
    """Ensure missing ASIN values use title-index fallback keys."""
    app = DummyTableApp()
    used: set[str] = set()
    key = app._build_row_key({"asin": None}, "Unknown Title", 3, used)
    assert key == "Unknown Title#3"
