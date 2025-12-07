"""Shared constants for the Auditui application."""

from pathlib import Path

AUTH_PATH = Path.home() / ".config" / "auditui" / "auth.json"
CACHE_DIR = Path.home() / ".cache" / "auditui" / "books"
DOWNLOAD_URL = "https://cde-ta-g7g.amazon.com/FionaCDEServiceEngine/FSDownloadContent"
DEFAULT_CODEC = "LC_128_44100_stereo"
MIN_FILE_SIZE = 1024 * 1024

TABLE_COLUMNS = ("Title", "Author", "Length", "Progress")

TABLE_CSS = """
Screen {
    background: #1e1e2e;
}

Header {
    background: #181825;
    color: #cdd6f4;
    text-style: bold;
}

Footer {
    background: #181825;
    color: #bac2de;
}

DataTable {
    height: 1fr;
    background: #1e1e2e;
    color: #cdd6f4;
    border: solid #585b70;
}

DataTable:focus {
    border: solid #89b4fa;
}

DataTable > .datatable--header {
    background: #45475a;
    color: #bac2de;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #313244;
    color: #cdd6f4;
}

DataTable > .datatable--odd-row {
    background: #181825;
}

DataTable > .datatable--even-row {
    background: #1e1e2e;
}

Static {
    height: 1;
    text-align: center;
    background: #181825;
    color: #cdd6f4;
}

Static#status {
    background: #181825;
    color: #bac2de;
}
"""
