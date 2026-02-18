"""Listening time and signup year from stats API; finished books count."""

from datetime import date
from typing import Any

from ..types import LibraryItem


def has_activity(stats: dict) -> bool:
    monthly_stats = stats.get("aggregated_monthly_listening_stats", [])
    return bool(
        monthly_stats and any(s.get("aggregated_sum", 0)
                              > 0 for s in monthly_stats)
    )


def get_listening_time(client: Any, duration: int, start_date: str) -> int:
    if not client:
        return 0
    try:
        stats = client.get(
            "1.0/stats/aggregates",
            monthly_listening_interval_duration=str(duration),
            monthly_listening_interval_start_date=start_date,
            store="Audible",
        )
        monthly_stats = stats.get("aggregated_monthly_listening_stats", [])
        return sum(s.get("aggregated_sum", 0) for s in monthly_stats)
    except Exception:
        return 0


def get_signup_year(client: Any) -> int:
    if not client:
        return 0
    current_year = date.today().year
    try:
        stats = client.get(
            "1.0/stats/aggregates",
            monthly_listening_interval_duration="12",
            monthly_listening_interval_start_date=f"{current_year}-01",
            store="Audible",
        )
        if not has_activity(stats):
            return 0
    except Exception:
        return 0
    left, right = 1995, current_year
    earliest_year = current_year
    while left <= right:
        middle = (left + right) // 2
        try:
            stats = client.get(
                "1.0/stats/aggregates",
                monthly_listening_interval_duration="12",
                monthly_listening_interval_start_date=f"{middle}-01",
                store="Audible",
            )
            has_activity_ = has_activity(stats)
        except Exception:
            has_activity_ = False
        if has_activity_:
            earliest_year = middle
            right = middle - 1
        else:
            left = middle + 1
    return earliest_year


def get_finished_books_count(
    library_client: Any, all_items: list[LibraryItem]
) -> int:
    if not library_client or not all_items:
        return 0
    return sum(1 for item in all_items if library_client.is_finished(item))
