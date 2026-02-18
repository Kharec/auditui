from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, cast

from auditui.ui import FilterScreen
from textual.widgets import Input


@dataclass(slots=True)
class DummyEvent:
    """Minimal event object carrying an input value for tests."""

    value: str


@dataclass(slots=True)
class FakeTimer:
    """Timer substitute recording whether stop() was called."""

    callback: Callable[[], None]
    stopped: bool = False

    def stop(self) -> None:
        """Mark timer as stopped."""
        self.stopped = True


def test_filter_debounce_uses_latest_value(monkeypatch) -> None:
    """Ensure debounce cancels previous timer and emits latest input value."""
    seen: list[str] = []
    timers: list[FakeTimer] = []

    def on_change(value: str) -> None:
        """Capture emitted filter values."""
        seen.append(value)

    screen = FilterScreen(on_change=on_change, debounce_seconds=0.2)

    def fake_set_timer(_delay: float, callback: Callable[[], None]) -> FakeTimer:
        """Record timer callbacks instead of scheduling real timers."""
        timer = FakeTimer(callback)
        timers.append(timer)
        return timer

    monkeypatch.setattr(screen, "set_timer", fake_set_timer)
    screen.on_input_changed(cast(Input.Changed, DummyEvent("a")))
    screen.on_input_changed(cast(Input.Changed, DummyEvent("ab")))
    assert len(timers) == 2
    assert timers[0].stopped is True
    assert timers[1].stopped is False
    timers[1].callback()
    assert seen == ["ab"]


def test_on_unmount_stops_pending_timer() -> None:
    """Ensure screen unmount stops pending debounce timer when present."""
    screen = FilterScreen(on_change=lambda _value: None)
    timer = FakeTimer(lambda: None)
    screen._debounce_timer = timer
    screen.on_unmount()
    assert timer.stopped is True
