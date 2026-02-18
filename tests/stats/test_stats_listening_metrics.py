from __future__ import annotations

from auditui.stats.listening import (
    get_finished_books_count,
    get_listening_time,
    get_signup_year,
    has_activity,
)


class StatsClient:
    """Client double for monthly aggregate lookups keyed by start date."""

    def __init__(self, sums_by_start_date: dict[str, list[int]]) -> None:
        """Store aggregate sums grouped by monthly_listening_interval_start_date."""
        self._sums = sums_by_start_date

    def get(self, path: str, **kwargs: str) -> dict:
        """Return aggregate payload based on requested interval start date."""
        del path
        start_date = kwargs["monthly_listening_interval_start_date"]
        sums = self._sums.get(start_date, [0])
        return {
            "aggregated_monthly_listening_stats": [{"aggregated_sum": s} for s in sums]
        }


def test_has_activity_detects_non_zero_months() -> None:
    """Ensure activity helper returns true when any month has positive sum."""
    assert (
        has_activity(
            {
                "aggregated_monthly_listening_stats": [
                    {"aggregated_sum": 0},
                    {"aggregated_sum": 1},
                ]
            }
        )
        is True
    )


def test_get_listening_time_sums_aggregated_months() -> None:
    """Ensure monthly aggregate sums are added into one listening total."""
    client = StatsClient({"2026-01": [1000, 2000, 3000]})
    assert get_listening_time(client, duration=1, start_date="2026-01") == 6000


def test_get_signup_year_returns_earliest_year_with_activity() -> None:
    """Ensure signup year search finds first active year via binary search."""
    client = StatsClient(
        {"2026-01": [1], "2010-01": [1], "2002-01": [1], "2001-01": [0]}
    )
    year = get_signup_year(client)
    assert year <= 2010


def test_get_finished_books_count_uses_library_is_finished() -> None:
    """Ensure finished books count delegates to library client predicate."""
    library_client = type(
        "Library", (), {"is_finished": lambda self, item: item.get("done", False)}
    )()
    items = [{"done": True}, {"done": False}, {"done": True}]
    assert get_finished_books_count(library_client, items) == 2
