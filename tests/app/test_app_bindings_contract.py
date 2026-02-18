from __future__ import annotations

from typing import TypeAlias

from auditui.app.bindings import BINDINGS
from textual.binding import Binding


BindingTuple: TypeAlias = tuple[str, str, str]
NormalizedBinding: TypeAlias = tuple[str, str, str, bool]

EXPECTED_BINDINGS: tuple[NormalizedBinding, ...] = (
    ("?", "show_help", "Help", False),
    ("s", "show_stats", "Stats", False),
    ("/", "filter", "Filter", False),
    ("escape", "clear_filter", "Clear filter", False),
    ("n", "sort", "Sort by name", False),
    ("p", "sort_by_progress", "Sort by progress", False),
    ("a", "show_all", "All/Unfinished", False),
    ("r", "refresh", "Refresh", False),
    ("enter", "play_selected", "Play", False),
    ("space", "toggle_playback", "Pause/Resume", True),
    ("left", "seek_backward", "-30s", False),
    ("right", "seek_forward", "+30s", False),
    ("ctrl+left", "previous_chapter", "Previous chapter", False),
    ("ctrl+right", "next_chapter", "Next chapter", False),
    ("up", "increase_speed", "Increase speed", False),
    ("down", "decrease_speed", "Decrease speed", False),
    ("f", "toggle_finished", "Mark finished", False),
    ("d", "toggle_download", "Download/Delete", False),
    ("q", "quit", "Quit", False),
)


def _normalize_binding(binding: Binding | BindingTuple) -> NormalizedBinding:
    """Return key, action, description, and priority from one binding item."""
    if isinstance(binding, Binding):
        return (binding.key, binding.action, binding.description, binding.priority)
    key, action, description = binding
    return (key, action, description, False)


def _all_bindings() -> list[NormalizedBinding]:
    """Normalize all app bindings into a stable comparable structure."""
    return [_normalize_binding(binding) for binding in BINDINGS]


def test_bindings_match_expected_shortcuts() -> None:
    """Ensure the shipped shortcut list stays stable and explicit."""
    assert _all_bindings() == list(EXPECTED_BINDINGS)


def test_binding_keys_are_unique() -> None:
    """Ensure each key is defined only once to avoid dispatch ambiguity."""
    keys = [binding[0] for binding in _all_bindings()]
    assert len(keys) == len(set(keys))
