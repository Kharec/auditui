from __future__ import annotations

from auditui.playback.chapters import get_current_chapter, get_current_chapter_index


CHAPTERS = [
    {"title": "One", "start_time": 0.0, "end_time": 60.0},
    {"title": "Two", "start_time": 60.0, "end_time": 120.0},
]


def test_get_current_chapter_handles_empty_chapter_list() -> None:
    """Ensure empty chapter metadata still returns a sensible fallback row."""
    assert get_current_chapter(12.0, [], 300.0) == ("Unknown Chapter", 12.0, 300.0)


def test_get_current_chapter_returns_matching_chapter_window() -> None:
    """Ensure chapter selection returns title and chapter-relative timing."""
    assert get_current_chapter(75.0, CHAPTERS, 120.0) == ("Two", 15.0, 60.0)


def test_get_current_chapter_falls_back_to_last_chapter() -> None:
    """Ensure elapsed values past known ranges map to last chapter."""
    assert get_current_chapter(150.0, CHAPTERS, 200.0) == ("Two", 90.0, 60.0)


def test_get_current_chapter_index_returns_none_without_chapters() -> None:
    """Ensure chapter index lookup returns None when no chapters exist."""
    assert get_current_chapter_index(10.0, []) is None


def test_get_current_chapter_index_returns_last_when_past_end() -> None:
    """Ensure chapter index lookup falls back to the final chapter index."""
    assert get_current_chapter_index(200.0, CHAPTERS) == 1
