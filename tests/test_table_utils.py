from auditui import table_utils


class StubLibrary:
    def extract_title(self, item: dict) -> str:
        return item.get("title", "")

    def extract_authors(self, item: dict) -> str:
        return item.get("authors", "")

    def extract_runtime_minutes(self, item: dict) -> int | None:
        return item.get("minutes")

    def format_duration(
        self, value: int | None, unit: str = "minutes", default_none: str | None = None
    ) -> str | None:
        if value is None:
            return default_none
        return f"{value}m"

    def extract_progress_info(self, item: dict) -> float | None:
        return item.get("percent")

    def extract_asin(self, item: dict) -> str | None:
        return item.get("asin")


class StubDownloads:
    def __init__(self, cached: set[str]) -> None:
        self._cached = cached

    def is_cached(self, asin: str) -> bool:
        return asin in self._cached


def test_create_title_sort_key_normalizes_accents() -> None:
    key_fn, _ = table_utils.create_title_sort_key()
    assert key_fn(["École"]) == "ecole"
    assert key_fn(["Zoo"]) == "zoo"


def test_create_progress_sort_key_parses_percent() -> None:
    key_fn, _ = table_utils.create_progress_sort_key()
    assert key_fn(["0", "0", "0", "42.5%"]) == 42.5
    assert key_fn(["0", "0", "0", "bad"]) == 0.0


def test_truncate_author_name() -> None:
    long_name = "A" * (table_utils.AUTHOR_NAME_MAX_LENGTH + 5)
    truncated = table_utils.truncate_author_name(long_name)
    assert truncated.endswith("...")
    assert len(truncated) <= table_utils.AUTHOR_NAME_MAX_LENGTH


def test_format_item_as_row_with_downloaded() -> None:
    library = StubLibrary()
    downloads = StubDownloads({"ASIN123"})
    item = {
        "title": "Title",
        "authors": "Author One",
        "minutes": 90,
        "percent": 12.34,
        "asin": "ASIN123",
    }
    title, author, runtime, progress, downloaded = table_utils.format_item_as_row(
        item, library, downloads
    )
    assert title == "Title"
    assert author == "Author One"
    assert runtime == "90m"
    assert progress == "12.3%"
    assert downloaded == "✓"


def test_format_item_as_row_zero_progress() -> None:
    library = StubLibrary()
    item = {"title": "Title", "authors": "Author",
            "minutes": 30, "percent": 0.0}
    _, _, _, progress, _ = table_utils.format_item_as_row(item, library, None)
    assert progress == "0%"
