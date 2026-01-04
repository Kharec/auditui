"""Shared constants for the Auditui application."""

from pathlib import Path

AUTH_PATH = Path.home() / ".config" / "auditui" / "auth.json"
CONFIG_PATH = Path.home() / ".config" / "auditui" / "config.json"
CACHE_DIR = Path.home() / ".cache" / "auditui" / "books"
DOWNLOAD_URL = "https://cde-ta-g7g.amazon.com/FionaCDEServiceEngine/FSDownloadContent"
DEFAULT_CODEC = "LC_128_44100_stereo"
MIN_FILE_SIZE = 1024 * 1024
DEFAULT_CHUNK_SIZE = 8192

TABLE_COLUMN_DEFS = (
    ("Title", 2),
    ("Author", 2),
    ("Length", 1),
    ("Progress", 1),
    ("Downloaded", 1),
)

AUTHOR_NAME_MAX_LENGTH = 40
AUTHOR_NAME_DISPLAY_LENGTH = 37
PROGRESS_COLUMN_INDEX = 3
SEEK_SECONDS = 30.0

TABLE_CSS = """
Screen {
    background: #141622;
}

#top_bar {
    background: #10131f;
    color: #d5d9f0;
    text-style: bold;
    height: 1;
    margin: 0;
    padding: 0;
}

#top_left,
#top_center,
#top_right {
    width: 1fr;
    padding: 0 1;
    background: #10131f;
    margin: 0;
}

#top_left {
    text-align: left;
}

#top_center {
    text-align: center;
}

#top_right {
    text-align: right;
}

DataTable {
    height: 1fr;
    background: #141622;
    color: #d6dbf2;
    border: solid #2b2f45;
    scrollbar-size-horizontal: 0;
}

DataTable:focus {
    border: solid #7aa2f7;
}

DataTable > .datatable--header {
    background: #1b2033;
    color: #b9c3e3;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #232842;
    color: #e6ebff;
}

DataTable > .datatable--odd-row {
    background: #121422;
}

DataTable > .datatable--even-row {
    background: #15182a;
}

Static {
    height: 1;
    text-align: center;
    background: #10131f;
    color: #c7cfe8;
}

Static#status {
    color: #b6bfdc;
}

Static#progress_info {
    color: #7aa2f7;
    text-style: bold;
    margin: 0;
    padding: 0;
}

ProgressBar#progress_bar {
    height: 1;
    background: #10131f;
    border: none;
    margin: 0;
    padding: 0 1;
    align: center middle;
}

ProgressBar#progress_bar > .progress-bar--track {
    background: #262a3f;
}

ProgressBar#progress_bar > .progress-bar--bar {
    background: #8bd5ca;
}

HelpScreen {
    align: center middle;
    background: rgba(0, 0, 0, 0.7);
}

HelpScreen Static {
    background: transparent;
}

StatsScreen {
    align: center middle;
    background: rgba(0, 0, 0, 0.7);
}

StatsScreen Static {
    background: transparent;
}

StatsScreen #help_container {
    width: auto;
    min-width: 55;
    max-width: 70;
}

StatsScreen #help_content {
    align: center middle;
    width: 100%;
}

StatsScreen .help_list {
    width: 100%;
}

StatsScreen .help_list > ListItem {
    background: transparent;
    height: 1;
}

StatsScreen .help_list > ListItem:hover {
    background: #232842;
}

StatsScreen .help_list > ListItem > Label {
    width: 100%;
    text-align: left;
    padding-left: 2;
}

#help_container {
    width: 88%;
    max-width: 120;
    min-width: 48;
    height: auto;
    max-height: 80%;
    min-height: 14;
    background: #181a2a;
    border: heavy #7aa2f7;
    padding: 1 2;
}

#help_title {
    width: 100%;
    height: 3;
    text-align: center;
    text-style: bold;
    color: #7aa2f7;
    content-align: center middle;
    margin-bottom: 1;
    border-bottom: solid #4b5165;
}

#help_content {
    width: 100%;
    height: auto;
    padding: 0;
    margin: 0 0 1 0;
}

.help_list {
    width: 1fr;
    height: auto;
    background: transparent;
    padding: 0 1;
    scrollbar-size: 0 0;
}

.help_list > ListItem {
    background: #1b1f33;
    padding: 0 1;
}

.help_list > ListItem:hover {
    background: #2a2f45;
}

.help_list > ListItem > Label {
    width: 100%;
    padding: 0;
}

#help_footer {
    width: 100%;
    height: 3;
    text-align: center;
    content-align: center middle;
    color: #bac2de;
    margin-top: 1;
    border-top: solid #4b5165;
}
"""
