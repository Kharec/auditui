from __future__ import annotations

from auditui.stats.format import format_date, format_time


def test_format_time_handles_minutes_and_hours() -> None:
    """Ensure format_time outputs minute-only and hour-minute formats."""
    assert format_time(90_000) == "1m"
    assert format_time(3_660_000) == "1h01"


def test_format_date_handles_iso_and_invalid_values() -> None:
    """Ensure format_date normalizes ISO timestamps and preserves invalid input."""
    assert format_date("2026-01-15T10:20:30Z") == "2026-01-15"
    assert format_date("not-a-date") == "not-a-date"
    assert format_date(None) == "Unknown"
