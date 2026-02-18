"""Playback position read and write helpers for library content."""

from __future__ import annotations

from typing import Any


class LibraryClientPositionsMixin:
    """Handles last-position retrieval and persistence."""

    client: Any

    def get_last_position(self, asin: str) -> float | None:
        """Get the last playback position for a book in seconds."""
        try:
            response = self.client.get(
                path="1.0/annotations/lastpositions",
                asins=asin,
            )
            annotations = response.get("asin_last_position_heard_annots", [])
            for annotation in annotations:
                if annotation.get("asin") != asin:
                    continue
                last_position_heard = annotation.get("last_position_heard", {})
                if not isinstance(last_position_heard, dict):
                    continue
                if last_position_heard.get("status") == "DoesNotExist":
                    return None
                position_ms = last_position_heard.get("position_ms")
                if position_ms is not None:
                    return float(position_ms) / 1000.0
            return None
        except (OSError, ValueError, KeyError):
            return None

    def _get_content_reference(self, asin: str) -> dict | None:
        """Fetch content reference payload used by position update calls."""
        try:
            response = self.client.get(
                path=f"1.0/content/{asin}/metadata",
                response_groups="content_reference",
            )
            content_metadata = response.get("content_metadata", {})
            content_reference = content_metadata.get("content_reference", {})
            if isinstance(content_reference, dict):
                return content_reference
            return None
        except (OSError, ValueError, KeyError):
            return None

    def _update_position(self, asin: str, position_seconds: float) -> bool:
        """Persist playback position to the API and return success state."""
        if position_seconds < 0:
            return False

        content_ref = self._get_content_reference(asin)
        if not content_ref:
            return False

        acr = content_ref.get("acr")
        if not acr:
            return False

        body = {
            "acr": acr,
            "asin": asin,
            "position_ms": int(position_seconds * 1000),
        }
        if version := content_ref.get("version"):
            body["version"] = version

        try:
            self.client.put(
                path=f"1.0/lastpositions/{asin}",
                body=body,
            )
            return True
        except (OSError, ValueError, KeyError):
            return False

    def save_last_position(self, asin: str, position_seconds: float) -> bool:
        """Save playback position to Audible and return success state."""
        if position_seconds <= 0:
            return False
        return self._update_position(asin, position_seconds)
