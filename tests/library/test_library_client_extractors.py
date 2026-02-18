from __future__ import annotations

from dataclasses import dataclass, field

from auditui.library import LibraryClient


@dataclass(slots=True)
class MockClient:
    """Client double that records writes and serves configurable responses."""

    put_calls: list[tuple[str, dict]] = field(default_factory=list)
    post_calls: list[tuple[str, dict]] = field(default_factory=list)
    _post_response: dict = field(default_factory=dict)
    raise_on_put: bool = False

    def put(self, path: str, body: dict) -> dict:
        """Record put payload or raise when configured."""
        if self.raise_on_put:
            raise RuntimeError("put failed")
        self.put_calls.append((path, body))
        return {}

    def post(self, path: str, body: dict) -> dict:
        """Record post payload and return configured response."""
        self.post_calls.append((path, body))
        return self._post_response

    def get(self, path: str, **kwargs: dict) -> dict:
        """Return empty data for extractor-focused tests."""
        del path, kwargs
        return {}


def build_item(
    *,
    title: str | None = None,
    product_title: str | None = None,
    authors: list[dict] | None = None,
    runtime_min: int | None = None,
    listening_status: dict | None = None,
    percent_complete: int | float | None = None,
    asin: str | None = None,
) -> dict:
    """Construct synthetic library items for extractor and finish tests."""
    item: dict = {}
    if title is not None:
        item["title"] = title
    if percent_complete is not None:
        item["percent_complete"] = percent_complete
    if listening_status is not None:
        item["listening_status"] = listening_status
    if asin is not None:
        item["asin"] = asin
    product: dict = {}
    if product_title is not None:
        product["title"] = product_title
    if runtime_min is not None:
        product["runtime_length"] = {"min": runtime_min}
    if authors is not None:
        product["authors"] = authors
    if asin is not None:
        product["asin"] = asin
    if product:
        item["product"] = product
    if runtime_min is not None:
        item["runtime_length_min"] = runtime_min
    return item


def test_extract_title_prefers_product_title() -> None:
    """Ensure product title has precedence over outer item title."""
    library = LibraryClient(MockClient())  # type: ignore[arg-type]
    assert (
        library.extract_title(build_item(title="Outer", product_title="Inner"))
        == "Inner"
    )


def test_extract_title_falls_back_to_asin() -> None:
    """Ensure title fallback uses product ASIN when no title exists."""
    library = LibraryClient(MockClient())  # type: ignore[arg-type]
    assert library.extract_title({"product": {"asin": "A1"}}) == "A1"


def test_extract_authors_joins_names() -> None:
    """Ensure author dictionaries are converted to a readable list."""
    library = LibraryClient(MockClient())  # type: ignore[arg-type]
    item = build_item(authors=[{"name": "A"}, {"name": "B"}])
    assert library.extract_authors(item) == "A, B"


def test_extract_runtime_minutes_handles_dict_and_number() -> None:
    """Ensure runtime extraction supports dict and numeric payloads."""
    library = LibraryClient(MockClient())  # type: ignore[arg-type]
    assert library.extract_runtime_minutes(build_item(runtime_min=12)) == 12
    assert library.extract_runtime_minutes({"runtime_length": 42}) == 42


def test_extract_progress_info_prefers_listening_status_when_needed() -> None:
    """Ensure progress can be sourced from listening_status when top-level is absent."""
    library = LibraryClient(MockClient())  # type: ignore[arg-type]
    item = build_item(listening_status={"percent_complete": 25.0})
    assert library.extract_progress_info(item) == 25.0


def test_extract_asin_prefers_item_then_product() -> None:
    """Ensure ASIN extraction works from both item and product fields."""
    library = LibraryClient(MockClient())  # type: ignore[arg-type]
    assert library.extract_asin(build_item(asin="ASIN1")) == "ASIN1"
    assert library.extract_asin({"product": {"asin": "ASIN2"}}) == "ASIN2"
