from __future__ import annotations

from auditui.app.progress import AppProgressMixin


class DummyPlayback:
    """Playback stub exposing periodic update method."""

    def __init__(self) -> None:
        """Initialize call counter."""
        self.saved_calls = 0

    def update_position_if_needed(self) -> None:
        """Increment call counter for assertions."""
        self.saved_calls += 1


class DummyProgressApp(AppProgressMixin):
    """Minimal app host containing playback dependency only."""

    def __init__(self) -> None:
        """Initialize playback stub."""
        self.playback = DummyPlayback()


def test_save_position_periodically_delegates_to_playback() -> None:
    """Ensure periodic save method delegates to playback updater."""
    app = DummyProgressApp()
    app._save_position_periodically()
    assert app.playback.saved_calls == 1
