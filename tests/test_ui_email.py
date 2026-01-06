import json
from pathlib import Path

import pytest

from auditui import ui


class DummyApp:
    def __init__(self) -> None:
        self.client = None
        self.auth = None
        self.library_client = None
        self.all_items = []
        self.BINDINGS = []


@pytest.fixture
def dummy_app() -> DummyApp:
    return DummyApp()


def test_find_email_in_data() -> None:
    screen = ui.StatsScreen()
    data = {"a": {"b": ["nope", "user@example.com"]}}
    assert screen._find_email_in_data(data) == "user@example.com"


def test_get_email_from_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, dummy_app: DummyApp
) -> None:
    screen = ui.StatsScreen()
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"email": "config@example.com"}))
    monkeypatch.setattr(ui, "CONFIG_PATH", config_path)

    email = screen._get_email_from_config(dummy_app)
    assert email == "config@example.com"


def test_get_email_from_auth_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, dummy_app: DummyApp
) -> None:
    screen = ui.StatsScreen()
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(json.dumps({"email": "auth@example.com"}))
    monkeypatch.setattr(ui, "AUTH_PATH", auth_path)

    email = screen._get_email_from_auth_file(dummy_app)
    assert email == "auth@example.com"


def test_get_email_from_auth(dummy_app: DummyApp) -> None:
    screen = ui.StatsScreen()

    class Auth:
        username = "user@example.com"
        login = None
        email = None

    dummy_app.auth = Auth()
    assert screen._get_email_from_auth(dummy_app) == "user@example.com"
