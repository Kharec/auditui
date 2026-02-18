from __future__ import annotations

from dataclasses import dataclass, field

from auditui.library import LibraryClient


@dataclass(slots=True)
class ProgressClient:
    """Client double for position and finished-state API methods."""

    get_responses: dict[str, dict] = field(default_factory=dict)
    put_calls: list[tuple[str, dict]] = field(default_factory=list)
    post_response: dict = field(default_factory=dict)
    fail_put: bool = False

    def get(self, path: str, **kwargs: object) -> dict:
        """Return preconfigured payloads by API path."""
        del kwargs
        return self.get_responses.get(path, {})

    def put(self, path: str, body: dict) -> dict:
        """Record payloads or raise to exercise error handling."""
        if self.fail_put:
            raise OSError("write failed")
        self.put_calls.append((path, body))
        return {}

    def post(self, path: str, body: dict) -> dict:
        """Return licenserequest response for ACR extraction."""
        del path, body
        return self.post_response


def test_is_finished_true_from_percent_complete() -> None:
    """Ensure 100 percent completion is treated as finished."""
    library = LibraryClient(ProgressClient())  # type: ignore[arg-type]
    assert library.is_finished({"percent_complete": 100}) is True


def test_get_last_position_reads_matching_annotation() -> None:
    """Ensure last position is read in seconds from matching annotation."""
    client = ProgressClient(
        get_responses={
            "1.0/annotations/lastpositions": {
                "asin_last_position_heard_annots": [
                    {"asin": "X", "last_position_heard": {"position_ms": 9000}}
                ]
            }
        }
    )
    library = LibraryClient(client)  # type: ignore[arg-type]
    assert library.get_last_position("X") == 9.0


def test_get_last_position_returns_none_for_missing_state() -> None:
    """Ensure DoesNotExist status is surfaced as no saved position."""
    client = ProgressClient(
        get_responses={
            "1.0/annotations/lastpositions": {
                "asin_last_position_heard_annots": [
                    {"asin": "X", "last_position_heard": {"status": "DoesNotExist"}}
                ]
            }
        }
    )
    library = LibraryClient(client)  # type: ignore[arg-type]
    assert library.get_last_position("X") is None


def test_save_last_position_validates_non_positive_values() -> None:
    """Ensure save_last_position short-circuits on non-positive input."""
    library = LibraryClient(ProgressClient())  # type: ignore[arg-type]
    assert library.save_last_position("A", 0) is False


def test_update_position_writes_version_when_available() -> None:
    """Ensure version is included in payload when metadata provides it."""
    client = ProgressClient(
        get_responses={
            "1.0/content/A/metadata": {
                "content_metadata": {
                    "content_reference": {"acr": "token", "version": "2"}
                }
            }
        }
    )
    library = LibraryClient(client)  # type: ignore[arg-type]
    assert library._update_position("A", 5.5) is True
    path, body = client.put_calls[0]
    assert path == "1.0/lastpositions/A"
    assert body["position_ms"] == 5500
    assert body["version"] == "2"


def test_mark_as_finished_updates_item_in_place() -> None:
    """Ensure successful finish update mutates local item flags."""
    client = ProgressClient(post_response={"content_license": {"acr": "token"}})
    library = LibraryClient(client)  # type: ignore[arg-type]
    item = {"runtime_length_min": 1, "listening_status": {}}
    assert library.mark_as_finished("ASIN", item) is True
    assert item["is_finished"] is True
    assert item["listening_status"]["is_finished"] is True
