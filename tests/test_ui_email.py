import json
from pathlib import Path

from auditui.stats.email import (
    find_email_in_data,
    get_email_from_auth,
    get_email_from_auth_file,
    get_email_from_config,
)


def test_find_email_in_data() -> None:
    data = {"a": {"b": ["nope", "user@example.com"]}}
    assert find_email_in_data(data) == "user@example.com"


def test_get_email_from_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"email": "config@example.com"}))
    assert get_email_from_config(config_path) == "config@example.com"


def test_get_email_from_auth_file(tmp_path: Path) -> None:
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(json.dumps({"email": "auth@example.com"}))
    assert get_email_from_auth_file(auth_path) == "auth@example.com"


def test_get_email_from_auth() -> None:
    class Auth:
        username = "user@example.com"
        login = None
        email = None

    assert get_email_from_auth(Auth()) == "user@example.com"
