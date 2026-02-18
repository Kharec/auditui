from __future__ import annotations

from auditui.app import state as state_mod


class DummyApp:
    """Lightweight app object for state initialization tests."""

    def __init__(self) -> None:
        """Expose update_status to satisfy init dependencies."""
        self.messages: list[str] = []

    def update_status(self, message: str) -> None:
        """Collect status updates for assertions."""
        self.messages.append(message)


def test_init_state_without_auth_or_client(monkeypatch) -> None:
    """Ensure baseline state is initialized when no auth/client is provided."""
    app = DummyApp()
    playback_args: list[tuple[object, object]] = []

    class FakePlayback:
        """Playback constructor recorder for init tests."""

        def __init__(self, notify, library_client) -> None:
            """Capture arguments passed by init_auditui_state."""
            playback_args.append((notify, library_client))

    monkeypatch.setattr(state_mod, "PlaybackController", FakePlayback)
    state_mod.init_auditui_state(app)
    assert app.library_client is None
    assert app.download_manager is None
    assert app.all_items == []
    assert app.current_items == []
    assert app.filter_text == ""
    assert app.show_all_mode is False
    assert playback_args and playback_args[0][1] is None


def test_init_state_with_auth_and_client_builds_dependencies(monkeypatch) -> None:
    """Ensure init constructs library, downloads, and playback dependencies."""
    app = DummyApp()
    auth = object()
    client = object()

    class FakeLibraryClient:
        """Fake library client constructor for dependency wiring checks."""

        def __init__(self, value) -> None:
            """Store constructor argument for assertions."""
            self.value = value

    class FakeDownloadManager:
        """Fake download manager constructor for dependency wiring checks."""

        def __init__(self, auth_value, client_value) -> None:
            """Store constructor arguments for assertions."""
            self.args = (auth_value, client_value)

    class FakePlayback:
        """Fake playback constructor for dependency wiring checks."""

        def __init__(self, notify, library_client) -> None:
            """Store constructor arguments for assertions."""
            self.notify = notify
            self.library_client = library_client

    monkeypatch.setattr(state_mod, "LibraryClient", FakeLibraryClient)
    monkeypatch.setattr(state_mod, "DownloadManager", FakeDownloadManager)
    monkeypatch.setattr(state_mod, "PlaybackController", FakePlayback)
    state_mod.init_auditui_state(app, auth=auth, client=client)
    assert isinstance(app.library_client, FakeLibraryClient)
    assert isinstance(app.download_manager, FakeDownloadManager)
    assert isinstance(app.playback, FakePlayback)
    assert app.library_client.value is client
    assert app.download_manager.args == (auth, client)
    assert app.playback.library_client.value is client
