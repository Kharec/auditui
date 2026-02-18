"""Seek, chapter, position save, and playback speed for the controller."""

from __future__ import annotations

import time

from . import chapters as chapters_mod
from . import seek as seek_mod
from .constants import MIN_SPEED, MAX_SPEED, SPEED_INCREMENT

from .controller_lifecycle import ControllerLifecycleMixin


class ControllerSeekSpeedMixin(ControllerLifecycleMixin):
    """Seek, chapter navigation, position persistence, and speed control."""

    def _seek(self, seconds: float, direction: str) -> bool:
        """Seek forward or backward by seconds via restart at new position. Returns True if done."""
        elapsed = self._get_current_elapsed()
        current = self.seek_offset + elapsed
        result = seek_mod.compute_seek_target(
            current, self.total_duration, seconds, direction
        )
        if result is None:
            self.notify("Already at end of file")
            return False
        new_position, message = result
        return self._restart_at_position(new_position, message=message)

    def seek_forward(self, seconds: float = 30.0) -> bool:
        """Seek forward by the given seconds. Returns True if seek was performed."""
        return self._seek(seconds, "forward")

    def seek_backward(self, seconds: float = 30.0) -> bool:
        """Seek backward by the given seconds. Returns True if seek was performed."""
        return self._seek(seconds, "backward")

    def get_current_progress(self) -> tuple[str, float, float] | None:
        """Return (chapter_title, chapter_elapsed, chapter_total) for progress display, or None."""
        if not self.is_playing or self.playback_start_time is None:
            return None
        elapsed = self._get_current_elapsed()
        total_elapsed = self.seek_offset + elapsed
        return chapters_mod.get_current_chapter(
            total_elapsed, self.chapters, self.total_duration
        )

    def seek_to_chapter(self, direction: str) -> bool:
        """Seek to the next or previous chapter. direction is 'next' or 'previous'. Returns True if done."""
        if not self.is_playing or not self.current_file_path:
            return False
        if not self.chapters:
            self.notify("No chapter information available")
            return False
        elapsed = self._get_current_elapsed()
        current_total = self.seek_offset + elapsed
        idx = chapters_mod.get_current_chapter_index(
            current_total, self.chapters)
        if idx is None:
            self.notify("Could not determine current chapter")
            return False
        if direction == "next":
            if idx >= len(self.chapters) - 1:
                self.notify("Already at last chapter")
                return False
            target = self.chapters[idx + 1]
            new_position = target["start_time"]
            message = f"Next chapter: {target['title']}"
        else:
            if idx <= 0:
                self.notify("Already at first chapter")
                return False
            target = self.chapters[idx - 1]
            new_position = target["start_time"]
            message = f"Previous chapter: {target['title']}"
        return self._restart_at_position(new_position, message=message)

    def seek_to_next_chapter(self) -> bool:
        """Seek to the next chapter. Returns True if seek was performed."""
        return self.seek_to_chapter("next")

    def seek_to_previous_chapter(self) -> bool:
        """Seek to the previous chapter. Returns True if seek was performed."""
        return self.seek_to_chapter("previous")

    def _save_current_position(self) -> None:
        """Persist current position to Audible via library_client."""
        if not (self.library_client and self.current_asin and self.is_playing):
            return
        if self.playback_start_time is None:
            return
        current_position = self.seek_offset + self._get_current_elapsed()
        if current_position <= 0:
            return
        try:
            self.library_client.save_last_position(
                self.current_asin, current_position)
        except (OSError, ValueError, KeyError):
            pass

    def update_position_if_needed(self) -> None:
        """Save position to Audible if the save interval has elapsed since last save."""
        if not (self.is_playing and self.library_client and self.current_asin):
            return
        current_time = time.time()
        if current_time - self.last_save_time >= self.position_save_interval:
            self._save_current_position()
            self.last_save_time = current_time

    def _change_speed(self, delta: float) -> bool:
        """Change speed by delta (clamped to MIN/MAX). Restarts playback. Returns True if changed."""
        new_speed = max(MIN_SPEED, min(MAX_SPEED, self.playback_speed + delta))
        if new_speed == self.playback_speed:
            return False
        elapsed = self._get_current_elapsed()
        current_total = self.seek_offset + elapsed
        return self._restart_at_position(
            current_total, new_speed, f"Speed: {new_speed:.2f}x"
        )

    def increase_speed(self) -> bool:
        """Increase playback speed. Returns True if speed was changed."""
        return self._change_speed(SPEED_INCREMENT)

    def decrease_speed(self) -> bool:
        """Decrease playback speed. Returns True if speed was changed."""
        return self._change_speed(-SPEED_INCREMENT)
