"""UI components for the Auditui application."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static


KEY_DISPLAY_MAP = {
    "ctrl+": "^",
    "left": "←",
    "right": "→",
    "up": "↑",
    "down": "↓",
    "space": "Space",
    "enter": "Enter",
}

KEY_COLOR = "#f9e2af"
DESC_COLOR = "#cdd6f4"


class HelpScreen(ModalScreen):
    """Help screen displaying all available keybindings."""

    BINDINGS = [("escape", "dismiss", "Close"), ("?", "dismiss", "Close")]

    @staticmethod
    def _format_key_display(key: str) -> str:
        """Format a key string for display with symbols."""
        result = key
        for old, new in KEY_DISPLAY_MAP.items():
            result = result.replace(old, new)
        return result

    @staticmethod
    def _parse_binding(binding: tuple | object) -> tuple[str, str]:
        """Extract key and description from a binding."""
        if isinstance(binding, tuple):
            key, _, description = binding
        else:
            key = binding.key
            description = binding.description
        return key, description

    def _make_item(self, binding: tuple | object) -> ListItem:
        """Create a ListItem for a single binding."""
        key, description = self._parse_binding(binding)
        key_display = self._format_key_display(key)
        text = f"[bold {KEY_COLOR}]{key_display:>12}[/]  [{DESC_COLOR}]{description}[/]"
        return ListItem(Label(text))

    def compose(self) -> ComposeResult:
        bindings = list(self.app.BINDINGS)
        mid = (len(bindings) + 1) // 2
        left_bindings = bindings[:mid]
        right_bindings = bindings[mid:]

        with Container(id="help_container"):
            yield Static("Key Bindings", id="help_title")
            with Horizontal(id="help_content"):
                yield ListView(
                    *[self._make_item(b) for b in left_bindings],
                    classes="help_list",
                )
                yield ListView(
                    *[self._make_item(b) for b in right_bindings],
                    classes="help_list",
                )
            yield Static(
                f"Press [bold {KEY_COLOR}]?[/] or [bold {KEY_COLOR}]Escape[/] to close",
                id="help_footer",
            )

    def action_dismiss(self) -> None:
        self.dismiss()
