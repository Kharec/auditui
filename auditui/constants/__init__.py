"""Compatibility exports for constants grouped by domain modules."""

from .downloads import DEFAULT_CHUNK_SIZE, DEFAULT_CODEC, DOWNLOAD_URL, MIN_FILE_SIZE
from .library import (
    AUTHOR_NAME_DISPLAY_LENGTH,
    AUTHOR_NAME_MAX_LENGTH,
    PROGRESS_COLUMN_INDEX,
)
from .paths import AUTH_PATH, CACHE_DIR, CONFIG_PATH
from .playback import SEEK_SECONDS
from .table import TABLE_COLUMN_DEFS
from .ui import TABLE_CSS


__all__ = [
    "AUTH_PATH",
    "CONFIG_PATH",
    "CACHE_DIR",
    "DOWNLOAD_URL",
    "DEFAULT_CODEC",
    "MIN_FILE_SIZE",
    "DEFAULT_CHUNK_SIZE",
    "TABLE_COLUMN_DEFS",
    "AUTHOR_NAME_MAX_LENGTH",
    "AUTHOR_NAME_DISPLAY_LENGTH",
    "PROGRESS_COLUMN_INDEX",
    "SEEK_SECONDS",
    "TABLE_CSS",
]
