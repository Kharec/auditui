"""Playback control via ffplay and position sync with Audible."""

from .controller import PlaybackController
from .media_info import load_media_info

__all__ = ["PlaybackController", "load_media_info"]
