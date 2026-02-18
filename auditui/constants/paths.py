"""Filesystem paths used by configuration and caching."""

from pathlib import Path


AUTH_PATH = Path.home() / ".config" / "auditui" / "auth.json"
CONFIG_PATH = Path.home() / ".config" / "auditui" / "config.json"
CACHE_DIR = Path.home() / ".cache" / "auditui" / "books"
