from __future__ import annotations

import json
from pathlib import Path

from auditui.stats.email import (
    find_email_in_data,
    first_email,
    get_email_from_account_info,
    get_email_from_auth,
    get_email_from_auth_file,
    get_email_from_config,
    resolve_email,
)


def test_find_email_in_nested_data() -> None:
    """Ensure nested structures are scanned until a plausible email is found."""
    data = {"a": {"b": ["nope", "user@example.com"]}}
    assert find_email_in_data(data) == "user@example.com"


def test_first_email_skips_unknown_and_none() -> None:
    """Ensure first_email ignores empty and Unknown sentinel values."""
    assert first_email(None, "Unknown", "ok@example.com") == "ok@example.com"


def test_get_email_from_config_and_auth_file(tmp_path: Path) -> None:
    """Ensure config and auth-file readers extract valid email fields."""
    config_path = tmp_path / "config.json"
    auth_path = tmp_path / "auth.json"
    config_path.write_text(
        json.dumps({"email": "config@example.com"}), encoding="utf-8"
    )
    auth_path.write_text(json.dumps({"email": "auth@example.com"}), encoding="utf-8")
    assert get_email_from_config(config_path) == "config@example.com"
    assert get_email_from_auth_file(auth_path) == "auth@example.com"


def test_get_email_from_auth_prefers_username() -> None:
    """Ensure auth object attributes are checked in expected precedence order."""
    auth = type(
        "Auth", (), {"username": "user@example.com", "login": None, "email": None}
    )()
    assert get_email_from_auth(auth) == "user@example.com"


def test_get_email_from_account_info_supports_nested_customer_info() -> None:
    """Ensure account email can be discovered in nested customer_info payload."""
    info = {"customer_info": {"primary_email": "nested@example.com"}}
    assert get_email_from_account_info(info) == "nested@example.com"


def test_resolve_email_falls_back_to_account_getter(tmp_path: Path) -> None:
    """Ensure resolve_email checks account-info callback when local sources miss."""
    auth = object()
    value = resolve_email(
        auth,
        client=object(),
        config_path=tmp_path / "missing-config.json",
        auth_path=tmp_path / "missing-auth.json",
        get_account_info=lambda: {"customer_email": "account@example.com"},
    )
    assert value == "account@example.com"
