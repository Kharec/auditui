"""Orchestrates ffplay process, position, chapters, seek, and speed; delegates to playback submodules."""

from __future__ import annotations

from ..library import LibraryClient
from ..types import StatusCallback

from .controller_seek_speed import ControllerSeekSpeedMixin
from .controller_lifecycle import ControllerLifecycleMixin
from .controller_state import ControllerStateMixin


class PlaybackController(ControllerSeekSpeedMixin, ControllerLifecycleMixin, ControllerStateMixin):
    """Controls ffplay: start/stop, pause/resume, seek, speed, and saving position to Audible."""
