"""UI components for the Auditui application."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Static


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

    def compose(self) -> ComposeResult:
        with Container(id="help_container"):
            yield Static("Key Bindings", id="help_title")
            with ScrollableContainer(id="help_content"):
                for binding in self.app.BINDINGS:
                    key, description = self._parse_binding(binding)
                    key_display = self._format_key_display(key)
                    with Horizontal(classes="help_row"):
                        yield Static(f"[bold {KEY_COLOR}]{key_display}[/]", classes="help_key")
                        yield Static(description, classes="help_action")
            yield Static(f"Press [bold {KEY_COLOR}]?[/] or [bold {KEY_COLOR}]Escape[/] to close", id="help_footer")

    def action_dismiss(self) -> None:
        self.dismiss()
