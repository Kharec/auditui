from __future__ import annotations

from pathlib import Path

import pytest

from auditui.constants import MIN_FILE_SIZE
from auditui.downloads import DownloadManager
from auditui.downloads import manager as manager_mod


def _bare_manager(tmp_path: Path) -> DownloadManager:
    """Create manager without invoking constructor side effects."""
    manager = DownloadManager.__new__(DownloadManager)
    manager.cache_dir = tmp_path
    manager.chunk_size = 1024
    manager.auth = type(
        "Auth", (), {"adp_token": "x", "locale": type("Loc", (), {"domain": "fr"})()}
    )()
    return manager


def test_get_activation_bytes_returns_hex(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Ensure activation bytes are converted to lowercase hex string."""
    manager = _bare_manager(tmp_path)
    monkeypatch.setattr(manager_mod, "get_activation_bytes", lambda _auth: b"\xde\xad")
    assert manager.get_activation_bytes() == "dead"


def test_get_activation_bytes_handles_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Ensure activation retrieval failures are handled gracefully."""
    manager = _bare_manager(tmp_path)

    def _boom(_auth: object) -> bytes:
        """Raise a deterministic failure for exception-path coverage."""
        raise OSError("no auth")

    monkeypatch.setattr(manager_mod, "get_activation_bytes", _boom)
    assert manager.get_activation_bytes() is None


def test_get_or_download_uses_cached_file_when_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure cached files bypass link generation and download work."""
    manager = _bare_manager(tmp_path)
    monkeypatch.setattr(manager, "_get_name_from_asin", lambda asin: "Book")
    cached_path = tmp_path / "Book.aax"
    cached_path.write_bytes(b"1" * MIN_FILE_SIZE)
    messages: list[str] = []
    assert manager.get_or_download("ASIN", notify=messages.append) == cached_path
    assert "Using cached file" in messages[0]


def test_get_or_download_reports_invalid_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure workflow reports invalid download URLs and aborts."""
    manager = _bare_manager(tmp_path)
    monkeypatch.setattr(manager, "_get_name_from_asin", lambda asin: "Book")
    monkeypatch.setattr(
        manager, "_get_download_link", lambda asin, notify=None: "ftp://bad"
    )
    messages: list[str] = []
    assert manager.get_or_download("ASIN", notify=messages.append) is None
    assert "Invalid download URL" in messages


def test_get_or_download_handles_download_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure workflow reports failures when stream download does not complete."""
    manager = _bare_manager(tmp_path)
    monkeypatch.setattr(manager, "_get_name_from_asin", lambda asin: "Book")
    monkeypatch.setattr(
        manager, "_get_download_link", lambda asin, notify=None: "https://ok"
    )
    monkeypatch.setattr(manager, "_download_file", lambda url, path, notify=None: None)
    messages: list[str] = []
    assert manager.get_or_download("ASIN", notify=messages.append) is None
    assert "Download failed" in messages
