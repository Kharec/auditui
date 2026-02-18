"""Elapsed playback time accounting for pauses."""

import time


def get_elapsed(
    playback_start_time: float | None,
    pause_start_time: float | None,
    paused_duration: float,
    is_paused: bool,
) -> float:
    """Return elapsed seconds since start, accounting for pauses."""
    if playback_start_time is None:
        return 0.0
    current_time = time.time()
    if is_paused and pause_start_time is not None:
        return (pause_start_time - playback_start_time) - paused_duration
    if pause_start_time is not None:
        paused_duration += current_time - pause_start_time
    return max(
        0.0,
        (current_time - playback_start_time) - paused_duration,
    )
