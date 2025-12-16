"""Utils for table operations."""

import unicodedata
from typing import Callable

from .constants import PROGRESS_COLUMN_INDEX


def create_title_sort_key(reverse: bool = False) -> tuple[Callable, bool]:
    """Create a sort key function for sorting by title."""
    def title_key(row_values):
        title_cell = row_values[0]
        if isinstance(title_cell, str):
            normalized = unicodedata.normalize('NFD', title_cell)
            return normalized.encode('ascii', 'ignore').decode('ascii').lower()
        return str(title_cell).lower()

    return title_key, reverse


def create_progress_sort_key(progress_column_index: int = PROGRESS_COLUMN_INDEX, reverse: bool = False) -> tuple[Callable, bool]:
    """Create a sort key function for sorting by progress percentage."""
    def progress_key(row_values):
        progress_cell = row_values[progress_column_index]
        if isinstance(progress_cell, str):
            try:
                return float(progress_cell.rstrip("%"))
            except (ValueError, AttributeError):
                return 0.0
        return 0.0

    return progress_key, reverse
