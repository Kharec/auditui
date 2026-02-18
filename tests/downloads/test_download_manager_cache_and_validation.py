from __future__ import annotations

from pathlib import Path
from typing import Any, cast

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
    """Ensure filename normalization uses ASCII words and dashes."""
    manager = DownloadManager.__new__(DownloadManager)
    assert (
        manager._sanitize_filename("Stephen King 11/22/63") == "Stephen-King-11-22-63"
    )


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
    monkeypatch.setattr(
        manager,
        "_get_filename_stems_from_asin",
        lambda asin: ["Stephen-King_11-22-63", "11-22-63"],
    )
    cached_path = tmp_path / "Stephen-King_11-22-63.aax"
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
    monkeypatch.setattr(
        manager,
        "_get_filename_stems_from_asin",
        lambda asin: ["Stephen-King_11-22-63", "11-22-63"],
    )
    cached_path = tmp_path / "Stephen-King_11-22-63.aax"
    cached_path.write_bytes(b"0" * (MIN_FILE_SIZE - 1))
    assert manager.get_cached_path("ASIN123") is None


def test_get_filename_stems_include_author_title_and_legacy_title() -> None:
    """Ensure filename candidates include new author_title and legacy title names."""
    manager = DownloadManager.__new__(DownloadManager)
    manager.client = cast(
        Any,
        type(
            "Client",
            (),
            {
                "get": lambda self, path, **kwargs: {
                    "product": {
                        "title": "11/22/63",
                        "authors": [{"name": "Stephen King"}],
                    }
                }
            },
        )(),
    )
    stems = manager._get_filename_stems_from_asin("B00TEST")
    assert stems[0] == "Stephen-King_11-22-63"
    assert "11-22-63" in stems
