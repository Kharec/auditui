"""Time and date formatting for stats display."""

from datetime import datetime


def format_time(milliseconds: int) -> str:
    total_seconds = int(milliseconds) // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h{minutes:02d}"
    return f"{minutes}m"


def format_date(date_str: str | None) -> str:
    if not date_str:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return date_str
