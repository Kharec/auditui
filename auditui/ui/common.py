"""Shared protocol, constants, and mixin for modal screens that need app context."""

from typing import Any, Protocol, cast


class _AppContext(Protocol):
    BINDINGS: list[tuple[str, str, str]]
    client: Any
    auth: Any
    library_client: Any
    all_items: list[dict]


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


class AppContextMixin:
    def _app(self) -> _AppContext:
        return cast(_AppContext, cast(Any, self).app)
