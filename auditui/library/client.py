"""Client facade for Audible library fetch, extraction, and progress updates."""

from __future__ import annotations

import audible

from .client_extract import LibraryClientExtractMixin
from .client_fetch import LibraryClientFetchMixin
from .client_finished import LibraryClientFinishedMixin
from .client_format import LibraryClientFormatMixin
from .client_positions import LibraryClientPositionsMixin


class LibraryClient(
    LibraryClientFetchMixin,
    LibraryClientExtractMixin,
    LibraryClientPositionsMixin,
    LibraryClientFinishedMixin,
    LibraryClientFormatMixin,
):
    """Audible library client composed from focused behavior mixins."""

    def __init__(self, client: audible.Client) -> None:
        """Store authenticated Audible client used by all operations."""
        self.client = client
