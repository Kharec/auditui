"""Shared constants for the Auditui application."""

from pathlib import Path

AUTH_PATH = Path.home() / ".config" / "auditui" / "auth.json"
CACHE_DIR = Path.home() / ".cache" / "auditui" / "books"
DOWNLOAD_URL = "https://cde-ta-g7g.amazon.com/FionaCDEServiceEngine/FSDownloadContent"
DEFAULT_CODEC = "LC_128_44100_stereo"
MIN_FILE_SIZE = 1024 * 1024
DEFAULT_CHUNK_SIZE = 8192

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
    height: 1;
    padding: 0 1;
    scrollbar-size: 0 0;
    overflow-x: hidden;
    overflow-y: hidden;
}

Footer > HorizontalGroup > KeyGroup,
Footer > HorizontalGroup > KeyGroup.-compact {
    margin: 0;
    padding: 0;
    background: #181825;
}

FooterKey,
FooterKey.-grouped,
Footer.-compact FooterKey {
    background: #181825;
    padding: 0;
    margin: 0 2 0 0;
}

FooterKey .footer-key--key {
    color: #f9e2af;
    background: #181825;
    text-style: bold;
    padding: 0 1 0 0;
}

FooterKey .footer-key--description {
    color: #cdd6f4;
    background: #181825;
    padding: 0;
}

FooterKey:hover {
    background: #313244;
    color: #cdd6f4;
}

FooterKey:hover .footer-key--key,
FooterKey:hover .footer-key--description {
    background: #313244;
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
    color: #bac2de;
}

Static#progress_info {
    color: #89b4fa;
    text-style: bold;
    margin: 0;
    padding: 0;
    width: 100%;
}

ProgressBar#progress_bar {
    height: 1;
    background: #181825;
    border: none;
    margin: 0;
    padding: 0 1;
    width: 100%;
    align: center middle;
}

ProgressBar#progress_bar > .progress-bar--track {
    background: #45475a;
}

ProgressBar#progress_bar > .progress-bar--bar {
    background: #a6e3a1;
    width: auto;
}
"""
