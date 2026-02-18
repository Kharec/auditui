from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from auditui.app.actions import AppActionsMixin


@dataclass(slots=True)
class FakeTable:
    """Minimal table shim exposing cursor and row count."""

    row_count: int
    cursor_row: int = 0


class DummyActionsApp(AppActionsMixin):
    """Minimal app host used for download naming hint tests."""

    def __init__(self) -> None:
        """Initialize state required by action helpers."""
        self.current_items: list[dict] = []
        self.download_manager = object()
        self.library_client = type(
            "Library", (), {"extract_asin": lambda self, item: item.get("asin")}
        )()
        self._table = FakeTable(row_count=0, cursor_row=0)

    def update_status(self, message: str) -> None:
        """Ignore status in this focused behavior test."""
        del message

    def query_one(self, selector: str, _type: object) -> FakeTable:
        """Return the fake table used in selection tests."""
        assert selector == "#library_table"
        return self._table


def test_action_toggle_download_passes_selected_item() -> None:
    """Ensure download toggle forwards selected item for naming hints."""
    app = DummyActionsApp()
    seen: list[tuple[str, str | None]] = []

    def capture_toggle(asin: str, item: dict | None = None) -> None:
        """Capture download toggle arguments for assertions."""
        seen.append((asin, item.get("title") if item else None))

    setattr(cast(Any, app), "_toggle_download_async", capture_toggle)
    app._table = FakeTable(row_count=1, cursor_row=0)
    app.current_items = [{"asin": "ASIN", "title": "Book"}]
    app.action_toggle_download()
    assert seen == [("ASIN", "Book")]
