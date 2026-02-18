"""Helpers for marking content as finished through Audible APIs."""

from __future__ import annotations

from typing import Any

from ..types import LibraryItem


class LibraryClientFinishedMixin:
    """Marks titles as finished and mutates in-memory item state."""

    client: Any

    def mark_as_finished(self, asin: str, item: LibraryItem | None = None) -> bool:
        """Mark a book as finished on Audible and optionally update item state."""
        total_ms = self._get_runtime_ms(asin, item)
        if not total_ms:
            return False

        acr = self._get_acr(asin)
        if not acr:
            return False

        try:
            self.client.put(
                path=f"1.0/lastpositions/{asin}",
                body={"asin": asin, "acr": acr, "position_ms": total_ms},
            )
            if item:
                item["is_finished"] = True
                listening_status = item.get("listening_status", {})
                if isinstance(listening_status, dict):
                    listening_status["is_finished"] = True
            return True
        except Exception:
            return False

    def _get_runtime_ms(self, asin: str, item: LibraryItem | None = None) -> int | None:
        """Return total runtime in milliseconds from item or metadata endpoint."""
        if item:
            extract_runtime_minutes = getattr(self, "extract_runtime_minutes")
            runtime_min = extract_runtime_minutes(item)
            if runtime_min:
                return runtime_min * 60 * 1000

        try:
            response = self.client.get(
                path=f"1.0/content/{asin}/metadata",
                response_groups="chapter_info",
            )
            chapter_info = response.get("content_metadata", {}).get("chapter_info", {})
            return chapter_info.get("runtime_length_ms")
        except Exception:
            return None

    def _get_acr(self, asin: str) -> str | None:
        """Fetch the ACR token required by finish/update write operations."""
        try:
            response = self.client.post(
                path=f"1.0/content/{asin}/licenserequest",
                body={
                    "response_groups": "content_reference",
                    "consumption_type": "Download",
                    "drm_type": "Adrm",
                },
            )
            return response.get("content_license", {}).get("acr")
        except Exception:
            return None
