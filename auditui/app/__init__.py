"""Main Textual app: table, bindings, and orchestration of library, playback, and downloads."""

from __future__ import annotations

from textual.app import App, ComposeResult

from ..constants import TABLE_CSS

from .bindings import BINDINGS
from .state import init_auditui_state
from .layout import AppLayoutMixin
from .table import AppTableMixin
from .library import AppLibraryMixin
from .actions import AppActionsMixin
from .progress import AppProgressMixin


class Auditui(App, AppProgressMixin, AppActionsMixin, AppLibraryMixin, AppTableMixin, AppLayoutMixin):
    """Orchestrates the library table, playback, downloads, filter, and modal screens."""

    SHOW_PALETTE = False
    BINDINGS = BINDINGS
    CSS = TABLE_CSS

    def compose(self) -> ComposeResult:
        yield from AppLayoutMixin.compose(self)

    def __init__(self, auth=None, client=None) -> None:
        super().__init__()
        init_auditui_state(self, auth, client)
