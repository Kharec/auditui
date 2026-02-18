"""Playback state: init, reset, elapsed time, process validation and signals."""

from __future__ import annotations

import signal
import time
from pathlib import Path

from ..library import LibraryClient
from ..types import StatusCallback

from . import elapsed as elapsed_mod
from . import process as process_mod


class ControllerStateMixin:
    """State attributes and helpers for process/signal handling."""

    def __init__(self, notify: StatusCallback, library_client: LibraryClient | None = None) -> None:
        self.notify = notify
        self.library_client = library_client
        self.playback_process = None
        self.is_playing = False
        self.is_paused = False
        self.current_file_path: Path | None = None
        self.current_asin: str | None = None
        self.playback_start_time: float | None = None
        self.paused_duration: float = 0.0
        self.pause_start_time: float | None = None
        self.total_duration: float | None = None
        self.chapters: list[dict] = []
        self.seek_offset: float = 0.0
        self.activation_hex: str | None = None
        self.last_save_time: float = 0.0
        self.position_save_interval: float = 30.0
        self.playback_speed: float = 1.0

    def _reset_state(self) -> None:
        """Clear playing/paused state and references to current file/asin."""
        self.playback_process = None
        self.is_playing = False
        self.is_paused = False
        self.current_file_path = None
        self.current_asin = None
        self.playback_start_time = None
        self.paused_duration = 0.0
        self.pause_start_time = None
        self.total_duration = None
        self.chapters = []
        self.seek_offset = 0.0
        self.activation_hex = None
        self.last_save_time = 0.0
        self.playback_speed = 1.0

    def _get_saved_state(self) -> dict:
        """Return a snapshot of path, asin, activation, duration, chapters, speed for restart."""
        return {
            "file_path": self.current_file_path,
            "asin": self.current_asin,
            "activation": self.activation_hex,
            "duration": self.total_duration,
            "chapters": self.chapters.copy(),
            "speed": self.playback_speed,
        }

    def _get_current_elapsed(self) -> float:
        """Return elapsed seconds since start, accounting for pauses."""
        if self.pause_start_time is not None and not self.is_paused:
            self.paused_duration += time.time() - self.pause_start_time
            self.pause_start_time = None
        return elapsed_mod.get_elapsed(
            self.playback_start_time,
            self.pause_start_time,
            self.paused_duration,
            self.is_paused,
        )

    def _stop_process(self) -> None:
        """Terminate the process and clear playing state without saving position."""
        process_mod.terminate_process(self.playback_process)
        self.playback_process = None
        self.is_playing = False
        self.is_paused = False
        self.playback_start_time = None
        self.paused_duration = 0.0
        self.pause_start_time = None

    def _validate_playback_state(self, require_paused: bool) -> bool:
        """Return True if process is running and paused state matches require_paused."""
        if not (self.playback_process and self.is_playing):
            return False
        if require_paused and not self.is_paused:
            return False
        if not require_paused and self.is_paused:
            return False
        if not self.is_alive():
            self.stop()
            self.notify("Playback process has ended")
            return False
        return True

    def _send_signal(self, sig: signal.Signals, status_prefix: str, action: str) -> None:
        """Send sig to the process, update is_paused, and notify."""
        if self.playback_process is None:
            return
        try:
            process_mod.send_signal(self.playback_process, sig)
            self.is_paused = sig == signal.SIGSTOP
            filename = self.current_file_path.name if self.current_file_path else None
            msg = f"{status_prefix}: {filename}" if filename else status_prefix
            self.notify(msg)
        except ProcessLookupError:
            self.stop()
            self.notify("Process no longer exists")
        except PermissionError:
            self.notify(f"Permission denied: cannot {action} playback")
        except (OSError, ValueError) as exc:
            self.notify(f"Error {action}ing playback: {exc}")

    def is_alive(self) -> bool:
        """Return True if the ffplay process is still running."""
        if self.playback_process is None:
            return False
        return self.playback_process.poll() is None
