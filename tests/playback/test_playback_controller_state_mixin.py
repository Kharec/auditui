from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from auditui.playback import controller_state as state_mod
from auditui.playback.controller import PlaybackController


class Proc:
    """Simple process shim exposing poll and pid for state tests."""

    def __init__(self, poll_value=None) -> None:
        """Store poll return value and fake pid."""
        self._poll_value = poll_value
        self.pid = 123

    def poll(self):
        """Return configured process status code or None."""
        return self._poll_value


def _controller() -> tuple[PlaybackController, list[str]]:
    """Build playback controller and collected notifications list."""
    messages: list[str] = []
    return PlaybackController(messages.append, None), messages


def test_get_current_elapsed_rolls_pause_into_duration(monkeypatch) -> None:
    """Ensure elapsed helper absorbs stale pause_start_time when resumed."""
    controller, _ = _controller()
    controller.pause_start_time = 100.0
    controller.is_paused = False
    monkeypatch.setattr(state_mod.time, "time", lambda: 120.0)
    monkeypatch.setattr(state_mod.elapsed_mod, "get_elapsed", lambda *args: 50.0)
    assert controller._get_current_elapsed() == 50.0
    assert controller.paused_duration == 20.0
    assert controller.pause_start_time is None


def test_validate_playback_state_stops_when_process_ended() -> None:
    """Ensure state validation stops and reports when process is gone."""
    controller, messages = _controller()
    controller.playback_process = cast(Any, Proc(poll_value=1))
    controller.is_playing = True
    controller.current_file_path = Path("book.aax")
    ok = controller._validate_playback_state(require_paused=False)
    assert ok is False
    assert messages[-1] == "Playback process has ended"


def test_send_signal_sets_paused_state_and_notifies(monkeypatch) -> None:
    """Ensure SIGSTOP updates paused state and includes filename in status."""
    controller, messages = _controller()
    controller.playback_process = cast(Any, Proc())
    controller.current_file_path = Path("book.aax")
    monkeypatch.setattr(state_mod.process_mod, "send_signal", lambda proc, sig: None)
    controller._send_signal(state_mod.signal.SIGSTOP, "Paused", "pause")
    assert controller.is_paused is True
    assert messages[-1] == "Paused: book.aax"


def test_send_signal_handles_process_lookup(monkeypatch) -> None:
    """Ensure missing process lookup errors are handled with user-facing message."""
    controller, messages = _controller()
    controller.playback_process = cast(Any, Proc())

    def raise_lookup(proc, sig):
        """Raise process lookup error to exercise exception path."""
        del proc, sig
        raise ProcessLookupError("gone")

    monkeypatch.setattr(state_mod.process_mod, "send_signal", raise_lookup)
    monkeypatch.setattr(state_mod.process_mod, "terminate_process", lambda proc: None)
    controller._send_signal(state_mod.signal.SIGCONT, "Playing", "resume")
    assert messages[-1] == "Process no longer exists"
