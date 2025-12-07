"""Playback control for Auditui."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
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

    def start(
        self, path: Path, activation_hex: str | None = None, status_callback: StatusCallback | None = None
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

        self._send_signal(signal.SIGSTOP, "Paused", "pause")

    def resume(self) -> None:
        """Resume the current playback."""
        if not self._validate_playback_state(require_paused=True):
            return

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
            filename = self.current_file_path.name if self.current_file_path else ""
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
