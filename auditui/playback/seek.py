"""Seek target computation: new position and message from direction and seconds."""


def compute_seek_target(
    current_position: float,
    total_duration: float | None,
    seconds: float,
    direction: str,
) -> tuple[float, str] | None:
    """Return (new_position, message) for a seek, or None if seek is invalid (e.g. at end)."""
    if direction == "forward":
        new_position = current_position + seconds
        if total_duration is not None:
            if new_position >= total_duration - 2:
                return None
            new_position = min(new_position, total_duration - 2)
        return (new_position, f"Skipped forward {int(seconds)}s")
    new_position = max(0.0, current_position - seconds)
    return (new_position, f"Skipped backward {int(seconds)}s")
