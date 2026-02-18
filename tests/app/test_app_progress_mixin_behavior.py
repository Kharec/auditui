from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from auditui.app.progress import AppProgressMixin
from textual.events import Key
from textual.widgets import DataTable


@dataclass(slots=True)
class FakeKeyEvent:
    """Minimal key event carrying key value and prevent_default state."""

    key: str
    prevented: bool = False

    def prevent_default(self) -> None:
        """Mark event as prevented."""
        self.prevented = True


@dataclass(slots=True)
class FakeStatic:
    """Minimal static widget with text and visibility fields."""

    display: bool = False
    text: str = ""

    def update(self, value: str) -> None:
        """Store rendered text value."""
        self.text = value


@dataclass(slots=True)
class FakeProgressBar:
    """Minimal progress bar widget storing latest progress value."""

    progress: float = 0.0

    def update(self, progress: float) -> None:
        """Store progress value for assertions."""
        self.progress = progress


@dataclass(slots=True)
class FakeContainer:
    """Minimal container exposing display property."""

    display: bool = False


class DummyPlayback:
    """Playback shim exposing only members used by AppProgressMixin."""

    def __init__(self) -> None:
        """Initialize playback state and update counters."""
        self.is_playing = False
        self._status: str | None = None
        self._progress: tuple[str, float, float] | None = None
        self.saved_calls = 0

    def check_status(self):
        """Return configurable status check message."""
        return self._status

    def get_current_progress(self):
        """Return configurable progress tuple."""
        return self._progress

    def update_position_if_needed(self) -> None:
        """Record periodic save invocations."""
        self.saved_calls += 1


class DummyProgressApp(AppProgressMixin):
    """Mixin host that records action dispatch and widget updates."""

    def __init__(self) -> None:
        """Initialize fake widgets and playback state."""
        self.playback = DummyPlayback()
        self.focused = object()
        self.actions: list[str] = []
        self.messages: list[str] = []
        self.progress_info = FakeStatic()
        self.progress_bar = FakeProgressBar()
        self.progress_container = FakeContainer()

    def action_seek_backward(self) -> None:
        """Record backward seek action dispatch."""
        self.actions.append("seek_backward")

    def action_toggle_playback(self) -> None:
        """Record toggle playback action dispatch."""
        self.actions.append("toggle")

    def update_status(self, message: str) -> None:
        """Capture status messages for assertions."""
        self.messages.append(message)

    def query_one(self, selector: str, _type: object):
        """Return fake widgets by selector used by progress mixin."""
        return {
            "#progress_info": self.progress_info,
            "#progress_bar": self.progress_bar,
            "#progress_bar_container": self.progress_container,
        }[selector]


def test_on_key_dispatches_seek_when_playing() -> None:
    """Ensure left key is intercepted and dispatched to seek action."""
    app = DummyProgressApp()
    app.playback.is_playing = True
    event = FakeKeyEvent("left")
    app.on_key(cast(Key, event))
    assert event.prevented is True
    assert app.actions == ["seek_backward"]


def test_on_key_dispatches_space_when_table_focused() -> None:
    """Ensure space is intercepted and dispatched when table is focused."""
    app = DummyProgressApp()
    app.focused = DataTable()
    event = FakeKeyEvent("space")
    app.on_key(cast(Key, event))
    assert event.prevented is True
    assert app.actions == ["toggle"]


def test_check_playback_status_hides_progress_after_message() -> None:
    """Ensure playback status message triggers hide-progress behavior."""
    app = DummyProgressApp()
    app.playback._status = "Finished"
    app._check_playback_status()
    assert app.messages[-1] == "Finished"
    assert app.progress_info.display is False
    assert app.progress_container.display is False


def test_update_progress_renders_visible_progress_row() -> None:
    """Ensure valid progress data updates widgets and makes them visible."""
    app = DummyProgressApp()
    app.playback.is_playing = True
    app.playback._progress = ("Chapter", 30.0, 60.0)
    app._update_progress()
    assert app.progress_bar.progress == 50.0
    assert app.progress_info.display is True
    assert app.progress_container.display is True
