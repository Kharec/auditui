"""UI components for the Auditui application."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Static


class HelpScreen(ModalScreen):
    """Help screen displaying all available keybindings."""

    BINDINGS = [("escape", "dismiss", "Close"), ("?", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Container(id="help_container"):
            yield Static("Key Bindings", id="help_title")
            with ScrollableContainer(id="help_content"):
                bindings = self.app.BINDINGS
                for binding in bindings:
                    if isinstance(binding, tuple):
                        key, action, description = binding
                    else:
                        key = binding.key
                        description = binding.description
                    key_display = key.replace(
                        "ctrl+", "^").replace("left", "←").replace("right", "→").replace("space", "Space").replace("enter", "Enter")
                    with Horizontal(classes="help_row"):
                        yield Static(f"[bold #f9e2af]{key_display}[/]", classes="help_key")
                        yield Static(description, classes="help_action")
            yield Static("Press [bold #f9e2af]?[/] or [bold #f9e2af]Escape[/] to close", id="help_footer")

    def action_dismiss(self) -> None:
        self.dismiss()
