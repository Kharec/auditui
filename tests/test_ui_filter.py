from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, cast

from auditui.ui import FilterScreen
from textual.widgets import Input


@dataclass(slots=True)
class DummyEvent:
    value: str


@dataclass(slots=True)
class FakeTimer:
    callback: Callable[[], None]
    stopped: bool = False

    def stop(self) -> None:
        self.stopped = True


def test_filter_debounce_uses_latest_value(monkeypatch) -> None:
    seen: list[str] = []
    timers: list[FakeTimer] = []

    def on_change(value: str) -> None:
        seen.append(value)

    screen = FilterScreen(on_change=on_change, debounce_seconds=0.2)

    def fake_set_timer(_delay: float, callback):
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
