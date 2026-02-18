from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from auditui.playback import controller_lifecycle as lifecycle_mod
from auditui.playback.controller import PlaybackController


class Proc:
    """Process shim used for lifecycle tests."""

    def __init__(self, poll_value=None) -> None:
        """Set initial poll result."""
        self._poll_value = poll_value

    def poll(self):
        """Return process running status."""
        return self._poll_value


def _controller() -> tuple[PlaybackController, list[str]]:
    """Build controller and message capture list."""
    messages: list[str] = []
    return PlaybackController(messages.append, None), messages


def test_start_reports_missing_ffplay(monkeypatch) -> None:
    """Ensure start fails fast when ffplay is unavailable."""
    controller, messages = _controller()
    monkeypatch.setattr(lifecycle_mod.process_mod, "is_ffplay_available", lambda: False)
    assert controller.start(Path("book.aax")) is False
    assert messages[-1] == "ffplay not found. Please install ffmpeg"


def test_start_sets_state_on_success(monkeypatch) -> None:
    """Ensure successful start initializes playback state and metadata."""
    controller, messages = _controller()
    monkeypatch.setattr(lifecycle_mod.process_mod, "is_ffplay_available", lambda: True)
    monkeypatch.setattr(
        lifecycle_mod.process_mod, "build_ffplay_cmd", lambda *args: ["ffplay"]
    )
    monkeypatch.setattr(
        lifecycle_mod.process_mod, "run_ffplay", lambda cmd: (Proc(None), None)
    )
    monkeypatch.setattr(
        lifecycle_mod,
        "load_media_info",
        lambda path, activation: (600.0, [{"title": "ch"}]),
    )
    monkeypatch.setattr(lifecycle_mod.time, "time", lambda: 100.0)
    ok = controller.start(
        Path("book.aax"), activation_hex="abcd", start_position=10.0, speed=1.2
    )
    assert ok is True
    assert controller.is_playing is True
    assert controller.current_file_path == Path("book.aax")
    assert controller.total_duration == 600.0
    assert messages[-1] == "Playing: book.aax"


def test_prepare_and_start_uses_last_position(monkeypatch) -> None:
    """Ensure prepare flow resumes from saved position when available."""
    messages: list[str] = []
    lib = type("Lib", (), {"get_last_position": lambda self, asin: 75.0})()
    controller = PlaybackController(messages.append, cast(Any, lib))
    started: list[tuple] = []

    class DM:
        """Download manager shim returning path and activation token."""

        def get_or_download(
            self,
            asin,
            notify,
            preferred_title: str | None = None,
            preferred_author: str | None = None,
        ):
            """Return deterministic downloaded file path."""
            del asin, notify, preferred_title, preferred_author
            return Path("book.aax")

        def get_activation_bytes(self):
            """Return deterministic activation token."""
            return "abcd"

    monkeypatch.setattr(controller, "start", lambda *args: started.append(args) or True)
    monkeypatch.setattr(lifecycle_mod.time, "time", lambda: 200.0)
    assert controller.prepare_and_start(cast(Any, DM()), "ASIN") is True
    assert started and started[0][3] == 75.0
    assert "Resuming from 01:15" in messages


def test_toggle_playback_uses_pause_and_resume_paths(monkeypatch) -> None:
    """Ensure toggle dispatches pause or resume based on paused flag."""
    controller, _ = _controller()
    controller.is_playing = True
    controller.playback_process = cast(Any, Proc(None))
    called: list[str] = []
    monkeypatch.setattr(controller, "pause", lambda: called.append("pause"))
    monkeypatch.setattr(controller, "resume", lambda: called.append("resume"))
    controller.is_paused = False
    assert controller.toggle_playback() is True
    controller.is_paused = True
    assert controller.toggle_playback() is True
    assert called == ["pause", "resume"]


def test_restart_at_position_restores_state_and_notifies(monkeypatch) -> None:
    """Ensure restart logic preserves metadata and emits custom message."""
    controller, messages = _controller()
    controller.is_playing = True
    controller.is_paused = True
    controller.current_file_path = Path("book.aax")
    controller.current_asin = "ASIN"
    controller.activation_hex = "abcd"
    controller.total_duration = 400.0
    controller.chapters = [{"title": "One"}]
    controller.playback_speed = 1.0
    monkeypatch.setattr(controller, "_stop_process", lambda: None)
    monkeypatch.setattr(lifecycle_mod.time, "sleep", lambda _s: None)
    monkeypatch.setattr(controller, "start", lambda *args: True)
    paused: list[str] = []
    monkeypatch.setattr(controller, "pause", lambda: paused.append("pause"))
    assert controller._restart_at_position(120.0, message="Jumped") is True
    assert controller.current_asin == "ASIN"
    assert controller.chapters == [{"title": "One"}]
    assert paused == ["pause"]
    assert messages[-1] == "Jumped"
