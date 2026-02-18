"""Playback lifecycle: start, stop, pause, resume, prepare_and_start, restart at position."""

from __future__ import annotations

import signal
import subprocess
import time
from pathlib import Path

from ..downloads import DownloadManager
from ..library import LibraryClient
from ..types import StatusCallback

from . import process as process_mod
from .media_info import load_media_info

from .controller_state import ControllerStateMixin


class ControllerLifecycleMixin(ControllerStateMixin):
    """Start/stop, pause/resume, and restart-at-position logic."""

    def start(
        self,
        path: Path,
        activation_hex: str | None = None,
        status_callback: StatusCallback | None = None,
        start_position: float = 0.0,
        speed: float | None = None,
    ) -> bool:
        """Start ffplay for the given AAX path. Returns True if playback started."""
        notify = status_callback or self.notify
        if not process_mod.is_ffplay_available():
            notify("ffplay not found. Please install ffmpeg")
            return False
        if self.playback_process is not None:
            self.stop()
        self.activation_hex = activation_hex
        self.seek_offset = start_position
        if speed is not None:
            self.playback_speed = speed
        cmd = process_mod.build_ffplay_cmd(
            path, activation_hex, start_position, self.playback_speed
        )
        try:
            proc, return_code = process_mod.run_ffplay(cmd)
            if proc is None:
                if (
                    return_code == 0
                    and start_position > 0
                    and self.total_duration
                    and start_position >= self.total_duration - 5
                ):
                    notify("Reached end of file")
                    self._reset_state()
                    return False
                notify(f"Playback process exited immediately (code: {return_code})")
                return False
            self.playback_process = proc
            self.is_playing = True
            self.is_paused = False
            self.current_file_path = path
            self.playback_start_time = time.time()
            self.paused_duration = 0.0
            self.pause_start_time = None
            duration, chs = load_media_info(path, activation_hex)
            self.total_duration = duration
            self.chapters = chs
            notify(f"Playing: {path.name}")
            return True
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            notify(f"Error starting playback: {exc}")
            return False

    def stop(self) -> None:
        """Stop ffplay, save position to Audible, and reset state."""
        if self.playback_process is None:
            return
        self._save_current_position()
        try:
            process_mod.terminate_process(self.playback_process)
        finally:
            self._reset_state()

    def pause(self) -> None:
        """Send SIGSTOP to ffplay and mark state as paused."""
        if not self._validate_playback_state(require_paused=False):
            return
        self.pause_start_time = time.time()
        self._send_signal(signal.SIGSTOP, "Paused", "pause")

    def resume(self) -> None:
        """Send SIGCONT to ffplay and clear paused state."""
        if not self._validate_playback_state(require_paused=True):
            return
        if self.pause_start_time is not None:
            self.paused_duration += time.time() - self.pause_start_time
            self.pause_start_time = None
        self._send_signal(signal.SIGCONT, "Playing", "resume")

    def check_status(self) -> str | None:
        """If the process has exited, return a status message and reset state; else None."""
        if self.playback_process is None:
            return None
        return_code = self.playback_process.poll()
        if return_code is None:
            return None
        finished_file = self.current_file_path
        self._reset_state()
        if finished_file:
            if return_code == 0:
                return f"Finished: {finished_file.name}"
            return f"Playback ended unexpectedly (code: {return_code}): {finished_file.name}"
        return "Playback finished"

    def prepare_and_start(
        self,
        download_manager: DownloadManager,
        asin: str,
        status_callback: StatusCallback | None = None,
        preferred_title: str | None = None,
        preferred_author: str | None = None,
    ) -> bool:
        """Download AAX if needed, get activation bytes, then start playback. Returns True on success."""
        notify = status_callback or self.notify
        if not download_manager:
            notify("Could not download file")
            return False
        notify("Preparing playback...")
        local_path = download_manager.get_or_download(
            asin,
            notify,
            preferred_title=preferred_title,
            preferred_author=preferred_author,
        )
        if not local_path:
            notify("Could not download file")
            return False
        notify("Getting activation bytes...")
        activation_hex = download_manager.get_activation_bytes()
        if not activation_hex:
            notify("Failed to get activation bytes")
            return False
        start_position = 0.0
        if self.library_client:
            try:
                last = self.library_client.get_last_position(asin)
                if last is not None and last > 0:
                    start_position = last
                    notify(f"Resuming from {LibraryClient.format_time(start_position)}")
            except (OSError, ValueError, KeyError):
                pass
        notify(f"Starting playback of {local_path.name}...")
        self.current_asin = asin
        self.last_save_time = time.time()
        return self.start(
            local_path, activation_hex, notify, start_position, self.playback_speed
        )

    def toggle_playback(self) -> bool:
        """Toggle between pause and resume. Returns True if an action was performed."""
        if not self.is_playing:
            return False
        if not self.is_alive():
            self.stop()
            self.notify("Playback has ended")
            return False
        if self.is_paused:
            self.resume()
        else:
            self.pause()
        return True

    def _restart_at_position(
        self,
        new_position: float,
        new_speed: float | None = None,
        message: str | None = None,
    ) -> bool:
        """Stop current process and start again at new_position; optionally set speed and notify."""
        if not self.is_playing or not self.current_file_path:
            return False
        was_paused = self.is_paused
        saved = self._get_saved_state()
        speed = new_speed if new_speed is not None else saved["speed"]
        self._stop_process()
        time.sleep(0.2)
        if self.start(
            saved["file_path"], saved["activation"], self.notify, new_position, speed
        ):
            self.current_asin = saved["asin"]
            self.total_duration = saved["duration"]
            self.chapters = saved["chapters"]
            if was_paused:
                time.sleep(0.3)
                self.pause()
            if message:
                self.notify(message)
            return True
        return False
