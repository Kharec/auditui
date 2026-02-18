"""Filter modal with input; returns filter string on dismiss."""

from typing import Callable

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import Input, Static

from .common import KEY_COLOR


class FilterScreen(ModalScreen[str]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(
        self,
        initial_filter: str = "",
        on_change: Callable[[str], None] | None = None,
        debounce_seconds: float = 0.2,
    ) -> None:
        super().__init__()
        self._initial_filter = initial_filter
        self._on_change = on_change
        self._debounce_seconds = debounce_seconds
        self._debounce_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        with Container(id="filter_container"):
            yield Static("Filter Library", id="filter_title")
            yield Input(
                value=self._initial_filter,
                placeholder="Type to filter by title or author...",
                id="filter_input",
            )
            yield Static(
                f"Press [bold {KEY_COLOR}]Enter[/] to apply, "
                f"[bold {KEY_COLOR}]Escape[/] to clear",
                id="filter_footer",
            )

    def on_mount(self) -> None:
        self.query_one("#filter_input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        callback = self._on_change
        if not callback:
            return
        if self._debounce_timer:
            self._debounce_timer.stop()
        value = event.value
        self._debounce_timer = self.set_timer(
            self._debounce_seconds,
            lambda: callback(value),
        )

    def action_cancel(self) -> None:
        self.dismiss("")

    def on_unmount(self) -> None:
        if self._debounce_timer:
            self._debounce_timer.stop()
