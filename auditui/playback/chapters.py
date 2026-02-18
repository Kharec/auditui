"""Chapter lookup by elapsed time."""


def get_current_chapter(
    elapsed: float,
    chapters: list[dict],
    total_duration: float | None,
) -> tuple[str, float, float]:
    """Return (title, elapsed_in_chapter, chapter_duration) for the chapter at elapsed time."""
    if not chapters:
        return ("Unknown Chapter", elapsed, total_duration or 0.0)
    for chapter in chapters:
        if chapter["start_time"] <= elapsed < chapter["end_time"]:
            chapter_elapsed = elapsed - chapter["start_time"]
            chapter_total = chapter["end_time"] - chapter["start_time"]
            return (chapter["title"], chapter_elapsed, chapter_total)
    last = chapters[-1]
    chapter_elapsed = max(0.0, elapsed - last["start_time"])
    chapter_total = last["end_time"] - last["start_time"]
    return (last["title"], chapter_elapsed, chapter_total)


def get_current_chapter_index(elapsed: float, chapters: list[dict]) -> int | None:
    """Return the index of the chapter containing the given elapsed time."""
    if not chapters:
        return None
    for idx, chapter in enumerate(chapters):
        if chapter["start_time"] <= elapsed < chapter["end_time"]:
            return idx
    return len(chapters) - 1
