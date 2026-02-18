from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from auditui.constants import MIN_FILE_SIZE
from auditui.downloads import DownloadManager
from auditui.downloads import manager as manager_mod


def _bare_manager(tmp_path: Path) -> DownloadManager:
    """Create manager without invoking constructor side effects."""
    manager = DownloadManager.__new__(DownloadManager)
    manager.cache_dir = tmp_path
    manager.chunk_size = 1024
    manager.auth = cast(
        Any,
        type(
            "Auth",
            (),
            {"adp_token": "x", "locale": type("Loc", (), {"domain": "fr"})()},
        )(),
    )
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
    monkeypatch.setattr(
        manager,
        "_get_filename_stems_from_asin",
        lambda asin, preferred_title=None, preferred_author=None: ["Author_Book"],
    )
    cached_path = tmp_path / "Author_Book.aax"
    cached_path.write_bytes(b"1" * MIN_FILE_SIZE)
    messages: list[str] = []
    assert manager.get_or_download("ASIN", notify=messages.append) == cached_path
    assert "Using cached file" in messages[0]


def test_get_or_download_reports_invalid_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure workflow reports invalid download URLs and aborts."""
    manager = _bare_manager(tmp_path)
    monkeypatch.setattr(
        manager,
        "_get_filename_stems_from_asin",
        lambda asin, preferred_title=None, preferred_author=None: ["Author_Book"],
    )
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
    monkeypatch.setattr(
        manager,
        "_get_filename_stems_from_asin",
        lambda asin, preferred_title=None, preferred_author=None: ["Author_Book"],
    )
    monkeypatch.setattr(
        manager, "_get_download_link", lambda asin, notify=None: "https://ok"
    )
    monkeypatch.setattr(manager, "_download_file", lambda url, path, notify=None: None)
    messages: list[str] = []
    assert manager.get_or_download("ASIN", notify=messages.append) is None
    assert "Download failed" in messages


def test_get_or_download_uses_preferred_naming_hints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure preferred title/author are forwarded to filename stem selection."""
    manager = _bare_manager(tmp_path)
    captured: list[tuple[str | None, str | None]] = []

    def stems(
        asin: str,
        preferred_title: str | None = None,
        preferred_author: str | None = None,
    ) -> list[str]:
        """Capture naming hints and return one deterministic filename stem."""
        del asin
        captured.append((preferred_title, preferred_author))
        return ["Author_Book"]

    monkeypatch.setattr(manager, "_get_filename_stems_from_asin", stems)
    monkeypatch.setattr(manager, "_get_download_link", lambda asin, notify=None: None)
    manager.get_or_download(
        "ASIN",
        preferred_title="11/22/63",
        preferred_author="Stephen King",
    )
    assert captured == [("11/22/63", "Stephen King")]


def test_get_or_download_retries_when_file_is_too_small(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure small downloads are retried and then reported with exact byte size."""
    manager = _bare_manager(tmp_path)
    monkeypatch.setattr(
        manager,
        "_get_filename_stems_from_asin",
        lambda asin, preferred_title=None, preferred_author=None: ["Author_Book"],
    )
    monkeypatch.setattr(
        manager, "_get_download_link", lambda asin, notify=None: "https://ok"
    )
    attempts = {"count": 0}

    def write_small_file(url: str, path: Path, notify=None) -> Path:
        """Write an undersized file to trigger retry and final failure messages."""
        del url, notify
        attempts["count"] += 1
        path.write_bytes(b"x" * 100)
        return path

    monkeypatch.setattr(manager, "_download_file", write_small_file)
    messages: list[str] = []
    assert manager.get_or_download("ASIN", notify=messages.append) is None
    assert attempts["count"] == 2
    assert any("retrying" in message for message in messages)
    assert any("file too small" in message for message in messages)
