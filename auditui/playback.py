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
from .library import LibraryClient

StatusCallback = Callable[[str], None]


class PlaybackController:
    """Manage playback through ffplay."""

    def __init__(self, notify: StatusCallback, library_client: LibraryClient | None = None) -> None:
        self.notify = notify
        self.library_client = library_client
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
        self.seek_offset: float = 0.0
        self.activation_hex: str | None = None
        self.last_save_time: float = 0.0
        self.position_save_interval: float = 30.0

    def start(
        self,
        path: Path,
        activation_hex: str | None = None,
        status_callback: StatusCallback | None = None,
        start_position: float = 0.0,
    ) -> bool:
        """Start playing a local file using ffplay."""
        notify = status_callback or self.notify

        if not shutil.which("ffplay"):
            notify("ffplay not found. Please install ffmpeg")
            return False

        if self.playback_process is not None:
            self.stop()

        self.activation_hex = activation_hex
        self.seek_offset = start_position

        cmd = ["ffplay", "-nodisp", "-autoexit"]
        if activation_hex:
            cmd.extend(["-activation_bytes", activation_hex])
        if start_position > 0:
            cmd.extend(["-ss", str(start_position)])
        cmd.append(str(path))

        try:
            self.playback_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            time.sleep(0.2)
            if self.playback_process.poll() is not None:
                return_code = self.playback_process.returncode
                if return_code == 0 and start_position > 0 and self.total_duration:
                    if start_position >= self.total_duration - 5:
                        notify("Reached end of file")
                        self._reset_state()
                        return False
                notify(
                    f"Playback process exited immediately (code: {return_code})")
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

        self._save_current_position()

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
        self.seek_offset = 0.0
        self.activation_hex = None
        self.last_save_time = 0.0

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

        start_position = 0.0
        if self.library_client:
            try:
                last_position = self.library_client.get_last_position(asin)
                if last_position is not None and last_position > 0:
                    start_position = last_position
                    notify(
                        f"Resuming from {self._format_position(start_position)}")
            except Exception:
                pass

        notify(f"Starting playback of {local_path.name}...")
        self.current_asin = asin
        self.last_save_time = time.time()
        return self.start(local_path, activation_hex, notify, start_position)

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

    def _get_current_elapsed(self) -> float:
        """Calculate current elapsed playback time."""
        if self.playback_start_time is None:
            return 0.0

        current_time = time.time()
        if self.is_paused and self.pause_start_time is not None:
            return (self.pause_start_time - self.playback_start_time) - self.paused_duration

        if self.pause_start_time is not None:
            self.paused_duration += current_time - self.pause_start_time
            self.pause_start_time = None

        return max(0.0, (current_time - self.playback_start_time) - self.paused_duration)

    def _stop_process(self) -> None:
        """Stop the playback process without resetting state."""
        if not self.playback_process:
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

        self.playback_process = None
        self.is_playing = False
        self.is_paused = False
        self.playback_start_time = None
        self.paused_duration = 0.0
        self.pause_start_time = None

    def _seek(self, seconds: float, direction: str) -> bool:
        """Seek forward or backward by specified seconds."""
        if not self.is_playing or not self.current_file_path:
            return False

        elapsed = self._get_current_elapsed()
        current_total_position = self.seek_offset + elapsed

        if direction == "forward":
            new_position = current_total_position + seconds
            if self.total_duration:
                if new_position >= self.total_duration - 2:
                    self.notify("Already at end of file")
                    return False
                new_position = min(new_position, self.total_duration - 2)
            message = f"Skipped forward {int(seconds)}s"
        else:
            new_position = max(0.0, current_total_position - seconds)
            message = f"Skipped backward {int(seconds)}s"

        was_paused = self.is_paused
        saved_state = {
            "file_path": self.current_file_path,
            "asin": self.current_asin,
            "activation": self.activation_hex,
            "duration": self.total_duration,
            "chapters": self.chapters.copy(),
        }

        self._stop_process()
        time.sleep(0.2)

        if self.start(saved_state["file_path"], saved_state["activation"], self.notify, new_position):
            self.current_asin = saved_state["asin"]
            self.total_duration = saved_state["duration"]
            self.chapters = saved_state["chapters"]
            if was_paused:
                time.sleep(0.3)
                self.pause()
            self.notify(message)
            return True
        return False

    def seek_forward(self, seconds: float = 30.0) -> bool:
        """Seek forward by specified seconds. Returns True if action was taken."""
        return self._seek(seconds, "forward")

    def seek_backward(self, seconds: float = 30.0) -> bool:
        """Seek backward by specified seconds. Returns True if action was taken."""
        return self._seek(seconds, "backward")

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

        elapsed = self._get_current_elapsed()
        total_elapsed = self.seek_offset + elapsed
        chapter_name, chapter_elapsed, chapter_total = self._get_current_chapter(
            total_elapsed)
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

    def _get_current_chapter_index(self, elapsed: float) -> int | None:
        """Get the index of the current chapter based on elapsed time."""
        if not self.chapters:
            return None

        for idx, chapter in enumerate(self.chapters):
            if chapter["start_time"] <= elapsed < chapter["end_time"]:
                return idx

        return len(self.chapters) - 1

    def seek_to_chapter(self, direction: str) -> bool:
        """Seek to next or previous chapter."""
        if not self.is_playing or not self.current_file_path:
            return False

        if not self.chapters:
            self.notify("No chapter information available")
            return False

        elapsed = self._get_current_elapsed()
        current_total_position = self.seek_offset + elapsed
        current_chapter_idx = self._get_current_chapter_index(
            current_total_position)

        if current_chapter_idx is None:
            self.notify("Could not determine current chapter")
            return False

        if direction == "next":
            if current_chapter_idx >= len(self.chapters) - 1:
                self.notify("Already at last chapter")
                return False
            target_chapter = self.chapters[current_chapter_idx + 1]
            new_position = target_chapter["start_time"]
            message = f"Next chapter: {target_chapter['title']}"
        else:
            if current_chapter_idx <= 0:
                self.notify("Already at first chapter")
                return False
            target_chapter = self.chapters[current_chapter_idx - 1]
            new_position = target_chapter["start_time"]
            message = f"Previous chapter: {target_chapter['title']}"

        was_paused = self.is_paused
        saved_state = {
            "file_path": self.current_file_path,
            "asin": self.current_asin,
            "activation": self.activation_hex,
            "duration": self.total_duration,
            "chapters": self.chapters.copy(),
        }

        self._stop_process()
        time.sleep(0.2)

        if self.start(saved_state["file_path"], saved_state["activation"], self.notify, new_position):
            self.current_asin = saved_state["asin"]
            self.total_duration = saved_state["duration"]
            self.chapters = saved_state["chapters"]
            if was_paused:
                time.sleep(0.3)
                self.pause()
            self.notify(message)
            return True
        return False

    def seek_to_next_chapter(self) -> bool:
        """Seek to the next chapter. Returns True if action was taken."""
        return self.seek_to_chapter("next")

    def seek_to_previous_chapter(self) -> bool:
        """Seek to the previous chapter. Returns True if action was taken."""
        return self.seek_to_chapter("previous")

    def _save_current_position(self) -> None:
        """Save the current playback position to Audible."""
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
        except Exception:
            pass

    def _format_position(self, seconds: float) -> str:
        """Format position in seconds as HH:MM:SS or MM:SS."""
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def update_position_if_needed(self) -> None:
        """Periodically save position if enough time has passed."""
        if not (self.is_playing and self.library_client and self.current_asin):
            return

        current_time = time.time()
        if current_time - self.last_save_time >= self.position_save_interval:
            self._save_current_position()
            self.last_save_time = current_time
