from __future__ import annotations

from pathlib import Path

import pytest

from auditui.constants import MIN_FILE_SIZE
from auditui.downloads import DownloadManager


def _manager_with_cache_dir(tmp_path: Path) -> DownloadManager:
    """Build a lightweight DownloadManager instance without real HTTP clients."""
    manager = DownloadManager.__new__(DownloadManager)
    manager.cache_dir = tmp_path
    manager.chunk_size = 1024
    return manager


def test_sanitize_filename_replaces_invalid_characters() -> None:
    """Ensure filesystem-invalid symbols are replaced with underscores."""
    manager = DownloadManager.__new__(DownloadManager)
    assert manager._sanitize_filename('a<>:"/\\|?*b') == "a_________b"


def test_validate_download_url_accepts_only_http_schemes() -> None:
    """Ensure download URL validation only accepts HTTP and HTTPS links."""
    manager = DownloadManager.__new__(DownloadManager)
    assert manager._validate_download_url("https://example.com/file") is True
    assert manager._validate_download_url("http://example.com/file") is True
    assert manager._validate_download_url("ftp://example.com/file") is False


def test_get_cached_path_and_remove_cached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure cache lookup and cache deletion work for valid files."""
    manager = _manager_with_cache_dir(tmp_path)
    monkeypatch.setattr(manager, "_get_name_from_asin", lambda asin: "My Book")
    cached_path = tmp_path / "My Book.aax"
    cached_path.write_bytes(b"0" * MIN_FILE_SIZE)
    messages: list[str] = []
    assert manager.get_cached_path("ASIN123") == cached_path
    assert manager.is_cached("ASIN123") is True
    assert manager.remove_cached("ASIN123", notify=messages.append) is True
    assert not cached_path.exists()
    assert "Removed from cache" in messages[-1]


def test_get_cached_path_ignores_small_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure undersized files are not treated as valid cache entries."""
    manager = _manager_with_cache_dir(tmp_path)
    monkeypatch.setattr(manager, "_get_name_from_asin", lambda asin: "My Book")
    cached_path = tmp_path / "My Book.aax"
    cached_path.write_bytes(b"0" * (MIN_FILE_SIZE - 1))
    assert manager.get_cached_path("ASIN123") is None
