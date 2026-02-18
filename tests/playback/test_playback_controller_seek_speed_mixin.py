from __future__ import annotations

from auditui.playback import controller_seek_speed as seek_speed_mod
from auditui.playback.controller import PlaybackController


def _controller() -> tuple[PlaybackController, list[str]]:
    """Build controller and in-memory notification sink."""
    messages: list[str] = []
    return PlaybackController(messages.append, None), messages


def test_seek_notifies_when_target_invalid(monkeypatch) -> None:
    """Ensure seek reports end-of-file condition when target is invalid."""
    controller, messages = _controller()
    monkeypatch.setattr(controller, "_get_current_elapsed", lambda: 20.0)
    controller.seek_offset = 100.0
    controller.total_duration = 120.0
    monkeypatch.setattr(
        seek_speed_mod.seek_mod, "compute_seek_target", lambda *args: None
    )
    assert controller._seek(30.0, "forward") is False
    assert messages[-1] == "Already at end of file"


def test_seek_to_chapter_reports_bounds(monkeypatch) -> None:
    """Ensure chapter seek reports first and last chapter boundaries."""
    controller, messages = _controller()
    controller.is_playing = True
    controller.current_file_path = object()
    controller.chapters = [{"title": "One", "start_time": 0.0, "end_time": 10.0}]
    monkeypatch.setattr(controller, "_get_current_elapsed", lambda: 1.0)
    monkeypatch.setattr(
        seek_speed_mod.chapters_mod,
        "get_current_chapter_index",
        lambda elapsed, chapters: 0,
    )
    assert controller.seek_to_chapter("next") is False
    assert messages[-1] == "Already at last chapter"
    assert controller.seek_to_chapter("previous") is False
    assert messages[-1] == "Already at first chapter"


def test_save_current_position_writes_positive_values() -> None:
    """Ensure save_current_position persists elapsed time via library client."""
    calls: list[tuple[str, float]] = []
    library = type(
        "Library",
        (),
        {"save_last_position": lambda self, asin, pos: calls.append((asin, pos))},
    )()
    controller = PlaybackController(lambda _msg: None, library)
    controller.current_asin = "ASIN"
    controller.is_playing = True
    controller.playback_start_time = 1.0
    controller.seek_offset = 10.0
    controller._get_current_elapsed = lambda: 15.0
    controller._save_current_position()
    assert calls == [("ASIN", 25.0)]


def test_update_position_if_needed_honors_interval(monkeypatch) -> None:
    """Ensure periodic save runs only when interval has elapsed."""
    controller, _ = _controller()
    controller.is_playing = True
    controller.current_asin = "ASIN"
    controller.library_client = object()
    controller.last_save_time = 10.0
    controller.position_save_interval = 30.0
    saves: list[str] = []
    monkeypatch.setattr(
        controller, "_save_current_position", lambda: saves.append("save")
    )
    monkeypatch.setattr(seek_speed_mod.time, "time", lambda: 20.0)
    controller.update_position_if_needed()
    monkeypatch.setattr(seek_speed_mod.time, "time", lambda: 45.0)
    controller.update_position_if_needed()
    assert saves == ["save"]


def test_change_speed_restarts_with_new_rate(monkeypatch) -> None:
    """Ensure speed changes restart playback at current position."""
    controller, _ = _controller()
    controller.playback_speed = 1.0
    controller.seek_offset = 5.0
    monkeypatch.setattr(controller, "_get_current_elapsed", lambda: 10.0)
    seen: list[tuple[float, float, str]] = []

    def fake_restart(
        position: float, speed: float | None = None, message: str | None = None
    ) -> bool:
        """Capture restart call parameters."""
        seen.append((position, speed or 0.0, message or ""))
        return True

    monkeypatch.setattr(controller, "_restart_at_position", fake_restart)
    assert controller.increase_speed() is True
    assert seen and seen[0][0] == 15.0
    assert seen[0][1] > 1.0
    assert seen[0][2].startswith("Speed: ")
