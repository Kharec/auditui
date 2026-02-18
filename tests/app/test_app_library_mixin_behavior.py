from __future__ import annotations

from auditui.app.library import AppLibraryMixin
from auditui.app import library as library_mod


class DummyLibraryApp(AppLibraryMixin):
    """Mixin host exposing only members used by AppLibraryMixin."""

    def __init__(self) -> None:
        """Initialize in-memory app state and call tracking."""
        self.all_items: list[dict] = []
        self.show_all_mode = False
        self._search_text_cache: dict[int, str] = {1: "x"}
        self.messages: list[str] = []
        self.call_log: list[tuple[str, tuple]] = []
        self.library_client = None

    def _prime_search_cache(self, items: list[dict]) -> None:
        """Store a marker so callers can assert this method was reached."""
        self.call_log.append(("prime", (items,)))

    def show_all(self) -> None:
        """Record show_all invocation for assertion."""
        self.call_log.append(("show_all", ()))

    def show_unfinished(self) -> None:
        """Record show_unfinished invocation for assertion."""
        self.call_log.append(("show_unfinished", ()))

    def update_status(self, message: str) -> None:
        """Capture status messages."""
        self.messages.append(message)

    def call_from_thread(self, func, *args) -> None:
        """Execute callback immediately to simplify tests."""
        func(*args)

    def _thread_status_update(self, message: str) -> None:
        """Capture worker-thread status update messages."""
        self.messages.append(message)


def test_on_library_loaded_refreshes_cache_and_shows_unfinished() -> None:
    """Ensure loaded items reset cache and default to unfinished view."""
    app = DummyLibraryApp()
    items = [{"asin": "a"}, {"asin": "b"}]
    app.on_library_loaded(items)
    assert app.all_items == items
    assert app._search_text_cache == {}
    assert app.messages[-1] == "Loaded 2 books"
    assert app.call_log[-1][0] == "show_unfinished"


def test_on_library_loaded_uses_show_all_mode() -> None:
    """Ensure loaded items respect show_all mode when enabled."""
    app = DummyLibraryApp()
    app.show_all_mode = True
    app.on_library_loaded([{"asin": "a"}])
    assert app.call_log[-1][0] == "show_all"


def test_on_library_error_formats_message() -> None:
    """Ensure library errors are surfaced through status updates."""
    app = DummyLibraryApp()
    app.on_library_error("boom")
    assert app.messages == ["Error fetching library: boom"]


def test_fetch_library_calls_on_loaded(monkeypatch) -> None:
    """Ensure fetch_library forwards fetched items through call_from_thread."""
    app = DummyLibraryApp()

    class Worker:
        """Simple worker shim exposing cancellation state."""

        is_cancelled = False

    class LibraryClient:
        """Fake client returning a deterministic item list."""

        def fetch_all_items(self, callback):
            """Invoke callback and return one item."""
            callback("progress")
            return [{"asin": "x"}]

    app.library_client = LibraryClient()
    monkeypatch.setattr(library_mod, "get_current_worker", lambda: Worker())
    AppLibraryMixin.fetch_library.__wrapped__(app)
    assert app.all_items == [{"asin": "x"}]
    assert "Loaded 1 books" in app.messages


def test_fetch_library_handles_expected_exception(monkeypatch) -> None:
    """Ensure fetch exceptions call on_library_error with error text."""
    app = DummyLibraryApp()

    class Worker:
        """Simple worker shim exposing cancellation state."""

        is_cancelled = False

    class BrokenClient:
        """Fake client raising an expected fetch exception."""

        def fetch_all_items(self, callback):
            """Raise the same exception family handled by mixin."""
            del callback
            raise ValueError("bad fetch")

    app.library_client = BrokenClient()
    monkeypatch.setattr(library_mod, "get_current_worker", lambda: Worker())
    AppLibraryMixin.fetch_library.__wrapped__(app)
    assert app.messages[-1] == "Error fetching library: bad fetch"
