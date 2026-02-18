from __future__ import annotations

from dataclasses import dataclass

from auditui.app.actions import AppActionsMixin


@dataclass(slots=True)
class FakeTable:
    """Minimal table shim exposing cursor and row count."""

    row_count: int
    cursor_row: int = 0


class FakePlayback:
    """Playback stub with togglable boolean return values."""

    def __init__(self, result: bool) -> None:
        """Store deterministic toggle result for tests."""
        self._result = result
        self.calls: list[str] = []

    def toggle_playback(self) -> bool:
        """Return configured result and record call."""
        self.calls.append("toggle")
        return self._result

    def seek_forward(self, _seconds: float) -> bool:
        """Return configured result and record call."""
        self.calls.append("seek_forward")
        return self._result


class DummyActionsApp(AppActionsMixin):
    """Mixin host with just enough state for action method tests."""

    def __init__(self) -> None:
        """Initialize fake app state used by action helpers."""
        self.messages: list[str] = []
        self.current_items: list[dict] = []
        self.download_manager = object()
        self.library_client = type(
            "Library", (), {"extract_asin": lambda self, item: item.get("asin")}
        )()
        self.playback = FakePlayback(True)
        self.filter_text = "hello"
        self._refreshed = 0
        self._table = FakeTable(row_count=0, cursor_row=0)

    def update_status(self, message: str) -> None:
        """Collect status messages for assertions."""
        self.messages.append(message)

    def query_one(self, selector: str, _type: object) -> FakeTable:
        """Return the fake table used in selection tests."""
        assert selector == "#library_table"
        return self._table

    def _refresh_filtered_view(self) -> None:
        """Record refresh invocations for filter tests."""
        self._refreshed += 1

    def _start_playback_async(self, asin: str) -> None:
        """Capture async playback launch argument."""
        self.messages.append(f"start:{asin}")


def test_get_selected_asin_requires_non_empty_table() -> None:
    """Ensure selection fails gracefully when table has no rows."""
    app = DummyActionsApp()
    app._table = FakeTable(row_count=0)
    assert app._get_selected_asin() is None
    assert app.messages[-1] == "No books available"


def test_get_selected_asin_returns_current_row_asin() -> None:
    """Ensure selected row index maps to current_items ASIN."""
    app = DummyActionsApp()
    app._table = FakeTable(row_count=2, cursor_row=1)
    app.current_items = [{"asin": "A1"}, {"asin": "A2"}]
    assert app._get_selected_asin() == "A2"


def test_action_play_selected_starts_async_playback() -> None:
    """Ensure play action calls async starter with selected ASIN."""
    app = DummyActionsApp()
    app._table = FakeTable(row_count=1, cursor_row=0)
    app.current_items = [{"asin": "ASIN"}]
    app.action_play_selected()
    assert app.messages[-1] == "start:ASIN"


def test_action_toggle_playback_shows_hint_when_no_playback() -> None:
    """Ensure toggle action displays no-playback hint on false return."""
    app = DummyActionsApp()
    app.playback = FakePlayback(False)
    app.action_toggle_playback()
    assert app.messages[-1] == "No playback active. Press Enter to play a book."


def test_action_seek_forward_shows_hint_when_seek_fails() -> None:
    """Ensure failed seek action reuses no-playback helper status."""
    app = DummyActionsApp()
    app.playback = FakePlayback(False)
    app.action_seek_forward()
    assert app.messages[-1] == "No playback active. Press Enter to play a book."


def test_action_clear_filter_resets_filter_and_refreshes() -> None:
    """Ensure clearing filter resets text and refreshes filtered view."""
    app = DummyActionsApp()
    app.action_clear_filter()
    assert app.filter_text == ""
    assert app._refreshed == 1
    assert app.messages[-1] == "Filter cleared"


def test_apply_filter_coerces_none_to_empty_string() -> None:
    """Ensure apply_filter normalizes None and refreshes list view."""
    app = DummyActionsApp()
    app._apply_filter(None)
    assert app.filter_text == ""
    assert app._refreshed == 1
