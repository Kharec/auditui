"""App state initialization."""

from __future__ import annotations

from ..constants import PROGRESS_COLUMN_INDEX
from ..downloads import DownloadManager
from ..library import LibraryClient
from ..playback import PlaybackController


def init_auditui_state(self: object, auth=None, client=None) -> None:
    setattr(self, "auth", auth)
    setattr(self, "client", client)
    setattr(self, "library_client", LibraryClient(client) if client else None)
    setattr(
        self,
        "download_manager",
        DownloadManager(auth, client) if auth and client else None,
    )
    notify = getattr(self, "update_status")
    lib_client = LibraryClient(client) if client else None
    setattr(self, "playback", PlaybackController(notify, lib_client))
    setattr(self, "all_items", [])
    setattr(self, "current_items", [])
    setattr(self, "_search_text_cache", {})
    setattr(self, "show_all_mode", False)
    setattr(self, "filter_text", "")
    setattr(self, "title_sort_reverse", False)
    setattr(self, "progress_sort_reverse", False)
    setattr(self, "title_column_key", None)
    setattr(self, "progress_column_index", PROGRESS_COLUMN_INDEX)
