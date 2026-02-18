"""Statistics modal showing listening time and account info via StatsAggregator."""

from datetime import date
from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static

from ..stats import StatsAggregator
from .common import KEY_COLOR, DESC_COLOR, AppContextMixin


class StatsScreen(AppContextMixin, ModalScreen):
    BINDINGS = [("escape", "dismiss", "Close"), ("s", "dismiss", "Close")]

    def _make_stat_item(self, label: str, value: str) -> ListItem:
        text = f"[bold {KEY_COLOR}]{label:>16}[/]  [{DESC_COLOR}]{value:<25}[/]"
        return ListItem(Label(text))

    def compose(self) -> ComposeResult:
        app = self._app()
        if not app.client:
            with Container(id="help_container"):
                yield Static("Statistics", id="help_title")
                yield Static(
                    "Not authenticated. Please restart and authenticate.",
                    classes="help_row",
                )
                yield Static(
                    f"Press [bold {KEY_COLOR}]s[/] or [bold {KEY_COLOR}]Escape[/] to close",
                    id="help_footer",
                )
            return
        aggregator = StatsAggregator(
            app.client, app.auth, app.library_client, app.all_items or []
        )
        stats_items = aggregator.get_stats(date.today())
        with Container(id="help_container"):
            yield Static("Statistics", id="help_title")
            with Vertical(id="help_content"):
                yield ListView(
                    *[self._make_stat_item(label, value)
                      for label, value in stats_items],
                    classes="help_list",
                )
            yield Static(
                f"Press [bold {KEY_COLOR}]s[/] or [bold {KEY_COLOR}]Escape[/] to close",
                id="help_footer",
            )

    async def action_dismiss(self, result: Any | None = None) -> None:
        await self.dismiss(result)
