from __future__ import annotations

import subprocess
from pathlib import Path

from auditui.playback import process as process_mod


class DummyProc:
    """Minimal subprocess-like object for terminate_process tests."""

    def __init__(self, alive: bool = True) -> None:
        """Initialize process state and bookkeeping flags."""
        self._alive = alive
        self.terminated = False
        self.killed = False
        self.pid = 123

    def poll(self) -> int | None:
        """Return None while process is alive and 0 when stopped."""
        return None if self._alive else 0

    def terminate(self) -> None:
        """Mark process as terminated and no longer alive."""
        self.terminated = True
        self._alive = False

    def wait(self, timeout: float | None = None) -> int:
        """Return immediately to emulate a cooperative shutdown."""
        del timeout
        return 0

    def kill(self) -> None:
        """Mark process as killed and no longer alive."""
        self.killed = True
        self._alive = False


def test_build_ffplay_cmd_includes_activation_seek_and_speed() -> None:
    """Ensure ffplay command includes optional playback arguments when set."""
    cmd = process_mod.build_ffplay_cmd(Path("book.aax"), "abcd", 12.5, 1.2)
    assert "-activation_bytes" in cmd
    assert "-ss" in cmd
    assert "atempo=1.20" in " ".join(cmd)


def test_terminate_process_handles_alive_process() -> None:
    """Ensure terminate_process gracefully shuts down a running process."""
    proc = DummyProc(alive=True)
    process_mod.terminate_process(proc)  # type: ignore[arg-type]
    assert proc.terminated is True


def test_run_ffplay_returns_none_when_unavailable(monkeypatch) -> None:
    """Ensure ffplay launch exits early when binary is not on PATH."""
    monkeypatch.setattr(process_mod, "is_ffplay_available", lambda: False)
    assert process_mod.run_ffplay(["ffplay", "book.aax"]) == (None, None)


def test_send_signal_delegates_to_os_kill(monkeypatch) -> None:
    """Ensure send_signal forwards process PID and signal to os.kill."""
    seen: list[tuple[int, object]] = []
    monkeypatch.setattr(
        process_mod.os, "kill", lambda pid, sig: seen.append((pid, sig))
    )
    process_mod.send_signal(DummyProc(), process_mod.signal.SIGSTOP)  # type: ignore[arg-type]
    assert seen and seen[0][0] == 123
