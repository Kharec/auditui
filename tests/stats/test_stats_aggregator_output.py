from __future__ import annotations

from datetime import date

from auditui.stats.aggregator import StatsAggregator
from auditui.stats import aggregator as aggregator_mod


def test_get_stats_returns_empty_without_client() -> None:
    """Ensure stats aggregation short-circuits when API client is absent."""
    aggregator = StatsAggregator(
        client=None, auth=None, library_client=None, all_items=[]
    )
    assert aggregator.get_stats() == []


def test_get_stats_builds_expected_rows(monkeypatch) -> None:
    """Ensure aggregator assembles rows from listening, account, and email sources."""
    monkeypatch.setattr(
        aggregator_mod.listening_mod, "get_signup_year", lambda _client: 2015
    )
    monkeypatch.setattr(
        aggregator_mod.listening_mod,
        "get_listening_time",
        lambda _client, duration, start_date: 120_000 if duration == 1 else 3_600_000,
    )
    monkeypatch.setattr(
        aggregator_mod.listening_mod, "get_finished_books_count", lambda _lc, _items: 7
    )
    monkeypatch.setattr(
        aggregator_mod.email_mod,
        "resolve_email",
        lambda *args, **kwargs: "user@example.com",
    )
    monkeypatch.setattr(aggregator_mod.account_mod, "get_country", lambda _auth: "US")
    monkeypatch.setattr(
        aggregator_mod.account_mod,
        "get_account_info",
        lambda _client: {
            "subscription_details": [
                {
                    "name": "Premium",
                    "next_bill_date": "2026-02-01T00:00:00Z",
                    "next_bill_amount": {
                        "currency_value": "14.95",
                        "currency_code": "USD",
                    },
                }
            ]
        },
    )

    aggregator = StatsAggregator(
        client=object(),
        auth=object(),
        library_client=object(),
        all_items=[{}, {}, {}],
    )
    stats = dict(aggregator.get_stats(today=date(2026, 2, 1)))
    assert stats["Email"] == "user@example.com"
    assert stats["Country Store"] == "US"
    assert stats["Signup Year"] == "2015"
    assert stats["Subscription"] == "Premium"
    assert stats["Price"] == "14.95 USD"
    assert stats["This Month"] == "2m"
    assert stats["This Year"] == "1h00"
    assert stats["Books Finished"] == "7 / 3"
