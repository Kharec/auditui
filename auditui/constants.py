"""Shared constants for the Auditui application."""

from pathlib import Path

AUTH_PATH = Path.home() / ".config" / "auditui" / "auth.json"
CACHE_DIR = Path.home() / ".cache" / "auditui" / "books"
DOWNLOAD_URL = "https://cde-ta-g7g.amazon.com/FionaCDEServiceEngine/FSDownloadContent"
DEFAULT_CODEC = "LC_128_44100_stereo"
MIN_FILE_SIZE = 1024 * 1024

TABLE_COLUMNS = ("Title", "Author", "Length", "Progress")

TABLE_CSS = """
DataTable {
    height: 1fr;
}
Static {
    height: 1;
    text-align: center;
    background: $primary;
}
"""

