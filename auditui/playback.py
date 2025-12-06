"""Playback control for Auditui."""

import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Callable


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

    def start(self, path: Path, activation_hex: str | None = None) -> bool:
        """Start playing a local file using ffplay."""
        if not shutil.which("ffplay"):
            self.notify("ffplay not found. Please install ffmpeg")
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
                self.notify(f"Playback process exited immediately (code: {return_code})")
                self.playback_process = None
                return False

            self.is_playing = True
            self.is_paused = False
            self.current_file_path = path
            self.notify(f"Playing: {path.name}")
            return True

        except Exception as exc:
            self.notify(f"Error starting playback: {exc}")
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
        except ProcessLookupError:
            pass
        except Exception:
            pass
        finally:
            self.playback_process = None
            self.is_playing = False
            self.is_paused = False
            self.current_file_path = None
            self.current_asin = None

    def pause(self) -> None:
        """Pause the current playback."""
        if not (self.playback_process and self.is_playing and not self.is_paused):
            return

        if not self.is_alive():
            self.stop()
            self.notify("Playback process has ended")
            return

        try:
            os.kill(self.playback_process.pid, signal.SIGSTOP)
            self.is_paused = True
            self.notify(self._status_message("Paused"))
        except ProcessLookupError:
            self.stop()
            self.notify("Process no longer exists")
        except PermissionError:
            self.notify("Permission denied: cannot pause playback")
        except Exception as exc:
            self.notify(f"Error pausing playback: {exc}")

    def resume(self) -> None:
        """Resume the current playback."""
        if not (self.playback_process and self.is_playing and self.is_paused):
            return

        if not self.is_alive():
            self.stop()
            self.notify("Playback process has ended")
            return

        try:
            os.kill(self.playback_process.pid, signal.SIGCONT)
            self.is_paused = False
            self.notify(self._status_message("Playing"))
        except ProcessLookupError:
            self.stop()
            self.notify("Process no longer exists")
        except PermissionError:
            self.notify("Permission denied: cannot resume playback")
        except Exception as exc:
            self.notify(f"Error resuming playback: {exc}")

    def check_status(self) -> str | None:
        """Check if playback process has finished and return status message."""
        if self.playback_process is None:
            return None

        return_code = self.playback_process.poll()
        if return_code is None:
            return None

        finished_file = self.current_file_path
        self.playback_process = None
        self.is_playing = False
        self.is_paused = False

        self.current_file_path = None
        self.current_asin = None

        if finished_file:
            if return_code == 0:
                return f"Finished: {finished_file.name}"
            return f"Playback ended unexpectedly (code: {return_code}): {finished_file.name}"
        return "Playback finished"

    def _status_message(self, prefix: str) -> str:
        """Generate status message with filename if available."""
        filename = self.current_file_path.name if self.current_file_path else ""
        return f"{prefix}: {filename}" if filename else prefix

    def is_alive(self) -> bool:
        """Check if playback process is still running."""
        if self.playback_process is None:
            return False
        return self.playback_process.poll() is None
