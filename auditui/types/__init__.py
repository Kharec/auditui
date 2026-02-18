"""Shared type aliases for the Audible TUI."""

from __future__ import annotations

from typing import Callable

LibraryItem = dict
StatusCallback = Callable[[str], None]
