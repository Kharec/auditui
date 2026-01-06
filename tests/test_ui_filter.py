from __future__ import annotations

from auditui.ui import FilterScreen


class DummyEvent:
    def __init__(self, value: str) -> None:
        self.value = value


class FakeTimer:
    def __init__(self, callback) -> None:
        self.callback = callback
        self.stopped = False

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

    screen.on_input_changed(DummyEvent("a"))
    screen.on_input_changed(DummyEvent("ab"))

    assert len(timers) == 2
    assert timers[0].stopped is True
    assert timers[1].stopped is False

    timers[1].callback()
    assert seen == ["ab"]
