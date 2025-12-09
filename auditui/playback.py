"""Playback control for Auditui."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Callable

from .downloads import DownloadManager

StatusCallback = Callable[[str], None]


class PlaybackController:
    """Manage playback through ffplay."""

    def __init__(self, notify: StatusCallback) -> None:
        self.notify = notify
        self.playback_process: subprocess.Popen | None = None
        self.is_playing = False
        self.is_paused = False
        self.current_file_path: Path | None = None
        self.current_asin: str | None = None
        self.playback_start_time: float | None = None
        self.paused_duration: float = 0.0
        self.pause_start_time: float | None = None
        self.total_duration: float | None = None
        self.chapters: list[dict] = []

    def start(
        self,
        path: Path,
        activation_hex: str | None = None,
        status_callback: StatusCallback | None = None,
    ) -> bool:
        """Start playing a local file using ffplay."""
        notify = status_callback or self.notify

        if not shutil.which("ffplay"):
            notify("ffplay not found. Please install ffmpeg")
            return False

        if self.playback_process is not None:
            self.stop()

        cmd = ["ffplay", "-nodisp", "-autoexit"]
        if activation_hex:
            cmd.extend(["-activation_bytes", activation_hex])
        cmd.append(str(path))

        try:
            self.playback_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            if self.playback_process.poll() is not None:
                return_code = self.playback_process.returncode
                notify(
                    f"Playback process exited immediately (code: {return_code})"
                )
                self.playback_process = None
                return False

            self.is_playing = True
            self.is_paused = False
            self.current_file_path = path
            self.playback_start_time = time.time()
            self.paused_duration = 0.0
            self.pause_start_time = None
            self._load_media_info(path, activation_hex)
            notify(f"Playing: {path.name}")
            return True

        except Exception as exc:
            notify(f"Error starting playback: {exc}")
            return False

    def stop(self) -> None:
        """Stop the current playback."""
        if self.playback_process is None:
            return

        try:
            if self.playback_process.poll() is None:
                self.playback_process.terminate()
                try:
                    self.playback_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.playback_process.kill()
                    self.playback_process.wait()
        except (ProcessLookupError, ValueError):
            pass
        finally:
            self._reset_state()

    def pause(self) -> None:
        """Pause the current playback."""
        if not self._validate_playback_state(require_paused=False):
            return

        self.pause_start_time = time.time()
        self._send_signal(signal.SIGSTOP, "Paused", "pause")

    def resume(self) -> None:
        """Resume the current playback."""
        if not self._validate_playback_state(require_paused=True):
            return

        if self.pause_start_time is not None:
            self.paused_duration += time.time() - self.pause_start_time
            self.pause_start_time = None
        self._send_signal(signal.SIGCONT, "Playing", "resume")

    def check_status(self) -> str | None:
        """Check if playback process has finished and return status message."""
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

    def _reset_state(self) -> None:
        """Reset all playback state."""
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

    def _validate_playback_state(self, require_paused: bool) -> bool:
        """Validate playback state before pause/resume operations."""
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
        """Send signal to playback process and update state."""
        if self.playback_process is None:
            return

        try:
            os.kill(self.playback_process.pid, sig)
            self.is_paused = sig == signal.SIGSTOP
            filename = self.current_file_path.name if self.current_file_path else None
            message = f"{status_prefix}: {filename}" if filename else status_prefix
            self.notify(message)
        except ProcessLookupError:
            self.stop()
            self.notify("Process no longer exists")
        except PermissionError:
            self.notify(f"Permission denied: cannot {action} playback")
        except Exception as exc:
            self.notify(f"Error {action}ing playback: {exc}")

    def is_alive(self) -> bool:
        """Check if playback process is still running."""
        if self.playback_process is None:
            return False
        return self.playback_process.poll() is None

    def prepare_and_start(
        self,
        download_manager: DownloadManager,
        asin: str,
        status_callback: StatusCallback | None = None,
    ) -> bool:
        """Download file, get activation bytes, and start playback."""
        notify = status_callback or self.notify

        if not download_manager:
            notify("Could not download file")
            return False

        notify("Preparing playback...")

        local_path = download_manager.get_or_download(asin, notify)
        if not local_path:
            notify("Could not download file")
            return False

        notify("Getting activation bytes...")
        activation_hex = download_manager.get_activation_bytes()
        if not activation_hex:
            notify("Failed to get activation bytes")
            return False

        notify(f"Starting playback of {local_path.name}...")
        self.current_asin = asin
        return self.start(local_path, activation_hex, notify)

    def toggle_playback(self) -> bool:
        """Toggle pause/resume state. Returns True if action was taken."""
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

    def _load_media_info(self, path: Path, activation_hex: str | None) -> None:
        """Load media information including duration and chapters using ffprobe."""
        if not shutil.which("ffprobe"):
            return

        try:
            cmd = ["ffprobe", "-v", "quiet", "-print_format",
                   "json", "-show_format", "-show_chapters"]
            if activation_hex:
                cmd.extend(["-activation_bytes", activation_hex])
            cmd.append(str(path))

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return

            data = json.loads(result.stdout)
            format_info = data.get("format", {})
            duration_str = format_info.get("duration")
            if duration_str:
                self.total_duration = float(duration_str)

            chapters_data = data.get("chapters", [])
            self.chapters = [
                {
                    "start_time": float(ch.get("start_time", 0)),
                    "end_time": float(ch.get("end_time", 0)),
                    "title": ch.get("tags", {}).get("title", f"Chapter {idx + 1}"),
                }
                for idx, ch in enumerate(chapters_data)
            ]
        except (json.JSONDecodeError, subprocess.TimeoutExpired, ValueError, KeyError):
            pass

    def get_current_progress(self) -> tuple[str, float, float] | None:
        """Get current playback progress."""
        if not self.is_playing or self.playback_start_time is None:
            return None

        current_time = time.time()
        if self.is_paused and self.pause_start_time is not None:
            elapsed = (self.pause_start_time -
                       self.playback_start_time) - self.paused_duration
        else:
            if self.pause_start_time is not None:
                self.paused_duration += current_time - self.pause_start_time
                self.pause_start_time = None
            elapsed = max(
                0.0, (current_time - self.playback_start_time) - self.paused_duration)

        chapter_name, chapter_elapsed, chapter_total = self._get_current_chapter(
            elapsed)
        return (chapter_name, chapter_elapsed, chapter_total)

    def _get_current_chapter(self, elapsed: float) -> tuple[str, float, float]:
        """Get current chapter info."""
        if not self.chapters:
            return ("Unknown Chapter", elapsed, self.total_duration or 0.0)

        for chapter in self.chapters:
            if chapter["start_time"] <= elapsed < chapter["end_time"]:
                chapter_elapsed = elapsed - chapter["start_time"]
                chapter_total = chapter["end_time"] - chapter["start_time"]
                return (chapter["title"], chapter_elapsed, chapter_total)

        last_chapter = self.chapters[-1]
        chapter_elapsed = max(0.0, elapsed - last_chapter["start_time"])
        chapter_total = last_chapter["end_time"] - last_chapter["start_time"]
        return (last_chapter["title"], chapter_elapsed, chapter_total)
