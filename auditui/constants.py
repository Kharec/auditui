"""Shared constants for the Auditui application."""

from pathlib import Path

AUTH_PATH = Path.home() / ".config" / "auditui" / "auth.json"
CACHE_DIR = Path.home() / ".cache" / "auditui" / "books"
DOWNLOAD_URL = "https://cde-ta-g7g.amazon.com/FionaCDEServiceEngine/FSDownloadContent"
DEFAULT_CODEC = "LC_128_44100_stereo"
MIN_FILE_SIZE = 1024 * 1024
DEFAULT_CHUNK_SIZE = 8192

TABLE_COLUMN_DEFS = (
    ("Title", 4),
    ("Author", 3),
    ("Length", 2),
    ("Progress", 1),
    ("Downloaded", 1),
)

AUTHOR_NAME_MAX_LENGTH = 40
AUTHOR_NAME_DISPLAY_LENGTH = 37
PROGRESS_COLUMN_INDEX = 3
SEEK_SECONDS = 30.0

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
    height: 2;
    padding: 0 1;
    scrollbar-size: 0 0;
    overflow-x: auto;
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
    margin: 0 1 0 0;
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
}

HelpScreen {
    align: center middle;
    background: rgba(0, 0, 0, 0.7);
}

#help_container {
    width: 70;
    height: auto;
    max-height: 85%;
    min-height: 20;
    background: #1e1e2e;
    border: thick #89b4fa;
    padding: 2;
}

#help_title {
    text-align: center;
    text-style: bold;
    color: #89b4fa;
    margin-bottom: 2;
    padding-bottom: 1;
    border-bottom: solid #585b70;
    height: 3;
    align: center middle;
}

#help_content {
    width: 100%;
    height: 1fr;
    padding: 1 0;
    margin: 1 0;
    overflow-y: auto;
    scrollbar-size: 0 1;
}

#help_content > .scrollbar--vertical {
    background: #313244;
}

#help_content > .scrollbar--vertical > .scrollbar--track {
    background: #181825;
}

#help_content > .scrollbar--vertical > .scrollbar--handle {
    background: #585b70;
}

#help_content > .scrollbar--vertical > .scrollbar--handle:hover {
    background: #45475a;
}

.help_row {
    height: 3;
    margin: 0 0 1 0;
    padding: 0 1;
    background: #181825;
    border: solid #313244;
    align: left middle;
}

.help_row:hover {
    background: #313244;
    border: solid #45475a;
}

.help_key {
    width: 20;
    text-align: right;
    padding: 0 2 0 0;
    color: #f9e2af;
    text-style: bold;
    align: right middle;
}

.help_action {
    width: 1fr;
    text-align: left;
    padding: 0 0 0 2;
    color: #cdd6f4;
    align: left middle;
}

#help_footer {
    text-align: center;
    color: #bac2de;
    margin-top: 2;
    padding-top: 1;
    border-top: solid #585b70;
    height: 3;
    align: center middle;
}
"""
