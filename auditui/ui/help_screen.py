"""Help modal that lists keybindings from the main app."""

from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static

from .common import KEY_COLOR, KEY_DISPLAY_MAP, DESC_COLOR, AppContextMixin

if TYPE_CHECKING:
    from textual.binding import Binding


class HelpScreen(AppContextMixin, ModalScreen):
    BINDINGS = [("escape", "dismiss", "Close"), ("?", "dismiss", "Close")]

    @staticmethod
    def _format_key_display(key: str) -> str:
        result = key
        for old, new in KEY_DISPLAY_MAP.items():
            result = result.replace(old, new)
        return result

    @staticmethod
    def _parse_binding(binding: "Binding | tuple[str, str, str]") -> tuple[str, str]:
        if isinstance(binding, tuple):
            return binding[0], binding[2]
        return binding.key, binding.description

    def _make_item(self, binding: "Binding | tuple[str, str, str]") -> ListItem:
        key, description = self._parse_binding(binding)
        key_display = self._format_key_display(key)
        text = f"[bold {KEY_COLOR}]{key_display:>16}[/]  [{DESC_COLOR}]{description:<25}[/]"
        return ListItem(Label(text))

    def compose(self) -> ComposeResult:
        app = self._app()
        bindings = list(app.BINDINGS)
        with Container(id="help_container"):
            yield Static("Keybindings", id="help_title")
            with Vertical(id="help_content"):
                yield ListView(
                    *[self._make_item(b) for b in bindings],
                    classes="help_list",
                )
            yield Static(
                f"Press [bold {KEY_COLOR}]?[/] or [bold {KEY_COLOR}]Escape[/] to close",
                id="help_footer",
            )

    async def action_dismiss(self, result: Any | None = None) -> None:
        await self.dismiss(result)
