"""Formatting helpers exposed by the library client."""

from __future__ import annotations


class LibraryClientFormatMixin:
    """Formats durations and timestamps for display usage."""

    @staticmethod
    def format_duration(
        value: int | None,
        unit: str = "minutes",
        default_none: str | None = None,
    ) -> str | None:
        """Format duration values as compact hour-minute strings."""
        if value is None or value <= 0:
            return default_none

        total_minutes = int(value)
        if unit == "seconds":
            total_minutes //= 60

        hours, minutes = divmod(total_minutes, 60)
        if hours > 0:
            return f"{hours}h{minutes:02d}" if minutes else f"{hours}h"
        return f"{minutes}m"

    @staticmethod
    def format_time(seconds: float) -> str:
        """Format seconds as HH:MM:SS or MM:SS for display."""
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
