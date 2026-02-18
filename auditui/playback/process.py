"""FFplay process: build command, spawn, terminate, and send signals."""

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path


def build_ffplay_cmd(
    path: Path,
    activation_hex: str | None,
    start_position: float,
    speed: float,
) -> list[str]:
    """Build the ffplay command line for the given path and options."""
    cmd = ["ffplay", "-nodisp", "-autoexit"]
    if activation_hex:
        cmd.extend(["-activation_bytes", activation_hex])
    if start_position > 0:
        cmd.extend(["-ss", str(start_position)])
    if speed != 1.0:
        cmd.extend(["-af", f"atempo={speed:.2f}"])
    cmd.append(str(path))
    return cmd


def is_ffplay_available() -> bool:
    """Return True if ffplay is on PATH."""
    return shutil.which("ffplay") is not None


def run_ffplay(cmd: list[str]) -> tuple[subprocess.Popen | None, int | None]:
    """Spawn ffplay. Returns (proc, None) on success, (None, return_code) if process exited immediately, (None, None) if ffplay missing or spawn failed."""
    if not is_ffplay_available():
        return (None, None)
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(0.2)
        if proc.poll() is not None:
            return (None, proc.returncode)
        return (proc, None)
    except (OSError, ValueError, subprocess.SubprocessError):
        return (None, None)


def terminate_process(proc: subprocess.Popen | None) -> None:
    """Terminate the process; kill if it does not exit within timeout."""
    if proc is None:
        return
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    except (ProcessLookupError, ValueError):
        pass


def send_signal(proc: subprocess.Popen, sig: signal.Signals) -> None:
    """Send sig to the process. May raise ProcessLookupError, PermissionError, OSError."""
    os.kill(proc.pid, sig)
