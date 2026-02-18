"""Key bindings for the main app."""

BINDINGS = [
    ("?", "show_help", "Help"),
    ("s", "show_stats", "Stats"),
    ("/", "filter", "Filter"),
    ("escape", "clear_filter", "Clear filter"),
    ("n", "sort", "Sort by name"),
    ("p", "sort_by_progress", "Sort by progress"),
    ("a", "show_all", "All/Unfinished"),
    ("r", "refresh", "Refresh"),
    ("enter", "play_selected", "Play"),
    ("space", "toggle_playback", "Pause/Resume"),
    ("left", "seek_backward", "-30s"),
    ("right", "seek_forward", "+30s"),
    ("ctrl+left", "previous_chapter", "Previous chapter"),
    ("ctrl+right", "next_chapter", "Next chapter"),
    ("up", "increase_speed", "Increase speed"),
    ("down", "decrease_speed", "Decrease speed"),
    ("f", "toggle_finished", "Mark finished"),
    ("d", "toggle_download", "Download/Delete"),
    ("q", "quit", "Quit"),
]
