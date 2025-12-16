"""Utils for table operations."""

import unicodedata
from typing import TYPE_CHECKING, Callable

from .constants import (
    AUTHOR_NAME_DISPLAY_LENGTH,
    AUTHOR_NAME_MAX_LENGTH,
    PROGRESS_COLUMN_INDEX,
)

if TYPE_CHECKING:
    from .downloads import DownloadManager


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


def truncate_author_name(author_names: str) -> str:
    """Truncate author name if it exceeds maximum length."""
    if author_names and len(author_names) > AUTHOR_NAME_MAX_LENGTH:
        return f"{author_names[:AUTHOR_NAME_DISPLAY_LENGTH]}..."
    return author_names


def format_item_as_row(item: dict, library_client, download_manager: "DownloadManager | None" = None) -> tuple[str, str, str, str, str]:
    """Format a library item into table row data.

    Returns:
        Tuple of (title, author, runtime, progress, downloaded) strings
    """
    title = library_client.extract_title(item)

    author_names = library_client.extract_authors(item)
    author_names = truncate_author_name(author_names)
    author_display = author_names or "Unknown"

    minutes = library_client.extract_runtime_minutes(item)
    runtime_str = library_client.format_duration(
        minutes, unit="minutes", default_none="Unknown length"
    ) or "Unknown"

    percent_complete = library_client.extract_progress_info(item)
    progress_str = (
        f"{percent_complete:.1f}%"
        if percent_complete and percent_complete > 0
        else "0%"
    )

    downloaded_str = ""
    if download_manager:
        asin = library_client.extract_asin(item)
        if asin and download_manager.is_cached(asin):
            downloaded_str = "✓"

    return (title, author_display, runtime_str, progress_str, downloaded_str)


def filter_unfinished_items(items: list[dict], library_client) -> list[dict]:
    """Filter out finished items from the list."""
    return [
        item for item in items
        if not library_client.is_finished(item)
    ]
