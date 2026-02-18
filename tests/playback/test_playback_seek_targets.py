from __future__ import annotations

from auditui.playback.seek import compute_seek_target


def test_forward_seek_returns_new_position_and_message() -> None:
    """Ensure forward seek computes expected position and status message."""
    target = compute_seek_target(10.0, 100.0, 30.0, "forward")
    assert target == (40.0, "Skipped forward 30s")


def test_forward_seek_returns_none_near_end() -> None:
    """Ensure seeking too close to end returns an invalid seek result."""
    assert compute_seek_target(95.0, 100.0, 10.0, "forward") is None


def test_backward_seek_clamps_to_zero() -> None:
    """Ensure backward seek cannot go below zero."""
    target = compute_seek_target(5.0, None, 30.0, "backward")
    assert target == (0.0, "Skipped backward 30s")
