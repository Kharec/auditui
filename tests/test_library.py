from auditui.library import LibraryClient


class MockClient:
    def __init__(self) -> None:
        self.put_calls: list[tuple[str, dict]] = []
        self.post_calls: list[tuple[str, dict]] = []
        self._post_response: dict = {}
        self.raise_on_put = False

    def put(self, path: str, body: dict) -> dict:
        if self.raise_on_put:
            raise RuntimeError("put failed")
        self.put_calls.append((path, body))
        return {}

    def post(self, path: str, body: dict) -> dict:
        self.post_calls.append((path, body))
        return self._post_response

    def get(self, path: str, **kwargs: dict) -> dict:
        return {}


def test_extract_title_prefers_product() -> None:
    client = MockClient()
    library = LibraryClient(client)  # type: ignore[arg-type]
    item = build_item(title="Outer", product_title="Inner")
    assert library.extract_title(item) == "Inner"


def test_extract_authors_joins_names() -> None:
    client = MockClient()
    library = LibraryClient(client)  # type: ignore[arg-type]
    item = build_item(authors=[{"name": "A"}, {"name": "B"}])
    assert library.extract_authors(item) == "A, B"


def test_extract_runtime_minutes_from_dict() -> None:
    client = MockClient()
    library = LibraryClient(client)  # type: ignore[arg-type]
    item = build_item(runtime_min=12)
    assert library.extract_runtime_minutes(item) == 12


def test_extract_progress_info_from_listening_status() -> None:
    client = MockClient()
    library = LibraryClient(client)  # type: ignore[arg-type]
    item = build_item(listening_status={"percent_complete": 25.0})
    assert library.extract_progress_info(item) == 25.0


def test_is_finished_with_percent_complete() -> None:
    client = MockClient()
    library = LibraryClient(client)  # type: ignore[arg-type]
    item = build_item(percent_complete=100)
    assert library.is_finished(item)


def test_format_duration_and_time() -> None:
    client = MockClient()
    library = LibraryClient(client)  # type: ignore[arg-type]
    assert library.format_duration(61) == "1h01"
    assert library.format_time(3661) == "01:01:01"


def test_mark_as_finished_success_updates_item() -> None:
    client = MockClient()
    client._post_response = {"content_license": {"acr": "token"}}
    library = LibraryClient(client)  # type: ignore[arg-type]
    item = build_item(runtime_min=1, listening_status={})
    ok = library.mark_as_finished("ASIN", item)
    assert ok
    assert client.put_calls
    path, body = client.put_calls[0]
    assert path == "1.0/lastpositions/ASIN"
    assert body["acr"] == "token"
    assert body["position_ms"] == 60_000
    assert item["is_finished"] is True
    assert item["listening_status"]["is_finished"] is True


def test_mark_as_finished_fails_without_acr() -> None:
    client = MockClient()
    client._post_response = {}
    library = LibraryClient(client)  # type: ignore[arg-type]
    item = build_item(runtime_min=1)
    ok = library.mark_as_finished("ASIN", item)
    assert ok is False


def test_mark_as_finished_handles_put_error() -> None:
    client = MockClient()
    client._post_response = {"content_license": {"acr": "token"}}
    client.raise_on_put = True
    library = LibraryClient(client)  # type: ignore[arg-type]
    item = build_item(runtime_min=1)
    ok = library.mark_as_finished("ASIN", item)
    assert ok is False


def build_item(
    *,
    title: str | None = None,
    product_title: str | None = None,
    authors: list[dict] | None = None,
    runtime_min: int | None = None,
    listening_status: dict | None = None,
    percent_complete: int | float | None = None,
) -> dict:
    item: dict = {}
    if title is not None:
        item["title"] = title
    if percent_complete is not None:
        item["percent_complete"] = percent_complete
    if listening_status is not None:
        item["listening_status"] = listening_status
    product: dict = {}
    if product_title is not None:
        product["title"] = product_title
    if runtime_min is not None:
        product["runtime_length"] = {"min": runtime_min}
    if authors is not None:
        product["authors"] = authors
    if product:
        item["product"] = product
    if runtime_min is not None and "runtime_length_min" not in item:
        item["runtime_length_min"] = runtime_min
    return item
