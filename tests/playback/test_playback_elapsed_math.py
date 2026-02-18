from __future__ import annotations

from auditui.playback.elapsed import get_elapsed
from auditui.playback import elapsed as elapsed_mod


def test_get_elapsed_returns_zero_without_start_time() -> None:
    """Ensure elapsed computation returns zero when playback has not started."""
    assert get_elapsed(None, None, 0.0, False) == 0.0


def test_get_elapsed_while_paused_uses_pause_start(monkeypatch) -> None:
    """Ensure paused elapsed is fixed at pause_start minus previous pauses."""
    monkeypatch.setattr(elapsed_mod.time, "time", lambda: 500.0)
    assert get_elapsed(100.0, 250.0, 20.0, True) == 130.0


def test_get_elapsed_subtracts_pause_duration_when_resumed(monkeypatch) -> None:
    """Ensure resumed elapsed removes newly accumulated paused duration."""
    monkeypatch.setattr(elapsed_mod.time, "time", lambda: 400.0)
    assert get_elapsed(100.0, 300.0, 10.0, False) == 190.0
