from pathlib import Path

import pytest

from auditui import downloads
from auditui.constants import MIN_FILE_SIZE


def test_sanitize_filename() -> None:
    dm = downloads.DownloadManager.__new__(downloads.DownloadManager)
    assert dm._sanitize_filename('a<>:"/\\|?*b') == "a_________b"


def test_validate_download_url() -> None:
    dm = downloads.DownloadManager.__new__(downloads.DownloadManager)
    assert dm._validate_download_url("https://example.com/file") is True
    assert dm._validate_download_url("http://example.com/file") is True
    assert dm._validate_download_url("ftp://example.com/file") is False


def test_cached_path_and_remove(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dm = downloads.DownloadManager.__new__(downloads.DownloadManager)
    dm.cache_dir = tmp_path

    monkeypatch.setattr(dm, "_get_name_from_asin", lambda asin: "My Book")
    safe_name = dm._sanitize_filename("My Book")
    cached_path = tmp_path / f"{safe_name}.aax"
    cached_path.write_bytes(b"0" * MIN_FILE_SIZE)

    assert dm.get_cached_path("ASIN123") == cached_path
    assert dm.is_cached("ASIN123") is True

    messages: list[str] = []
    assert dm.remove_cached("ASIN123", notify=messages.append) is True
    assert not cached_path.exists()
    assert messages and "Removed from cache" in messages[-1]


def test_cached_path_ignores_small_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dm = downloads.DownloadManager.__new__(downloads.DownloadManager)
    dm.cache_dir = tmp_path

    monkeypatch.setattr(dm, "_get_name_from_asin", lambda asin: "My Book")
    safe_name = dm._sanitize_filename("My Book")
    cached_path = tmp_path / f"{safe_name}.aax"
    cached_path.write_bytes(b"0" * (MIN_FILE_SIZE - 1))

    assert dm.get_cached_path("ASIN123") is None
