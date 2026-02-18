from __future__ import annotations

from auditui.stats.account import (
    get_account_info,
    get_country,
    get_subscription_details,
)


class AccountClient:
    """Minimal API client returning endpoint-specific account responses."""

    def __init__(self, responses: dict[str, dict]) -> None:
        """Store endpoint response map for deterministic tests."""
        self._responses = responses

    def get(self, path: str, **kwargs: object) -> dict:
        """Return configured response and ignore query parameters."""
        del kwargs
        return self._responses.get(path, {})


def test_get_account_info_merges_multiple_endpoints() -> None:
    """Ensure account info aggregator combines endpoint payload dictionaries."""
    client = AccountClient(
        {
            "1.0/account/information": {"a": 1},
            "1.0/customer/information": {"b": 2},
            "1.0/customer/status": {"c": 3},
        }
    )
    assert get_account_info(client) == {"a": 1, "b": 2, "c": 3}


def test_get_subscription_details_uses_known_nested_paths() -> None:
    """Ensure first valid subscription_details list entry is returned."""
    info = {
        "customer_details": {
            "subscription": {"subscription_details": [{"name": "Plan"}]}
        }
    }
    assert get_subscription_details(info) == {"name": "Plan"}


def test_get_country_supports_locale_variants() -> None:
    """Ensure country extraction supports object, domain, and locale string forms."""
    auth_country_code = type(
        "Auth", (), {"locale": type("Loc", (), {"country_code": "us"})()}
    )()
    auth_domain = type("Auth", (), {"locale": type("Loc", (), {"domain": "fr"})()})()
    auth_string = type("Auth", (), {"locale": "en_gb"})()
    assert get_country(auth_country_code) == "US"
    assert get_country(auth_domain) == "FR"
    assert get_country(auth_string) == "GB"
