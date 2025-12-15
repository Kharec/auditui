"""Media information loading for Audible content."""

import json
import shutil
import subprocess
from pathlib import Path


def load_media_info(path: Path, activation_hex: str | None = None) -> tuple[float | None, list[dict]]:
    """Load media information including duration and chapters using ffprobe."""
    if not shutil.which("ffprobe"):
        return None, []

    try:
        cmd = ["ffprobe", "-v", "quiet", "-print_format",
               "json", "-show_format", "-show_chapters"]
        if activation_hex:
            cmd.extend(["-activation_bytes", activation_hex])
        cmd.append(str(path))

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return None, []

        data = json.loads(result.stdout)
        format_info = data.get("format", {})
        duration_str = format_info.get("duration")
        duration = float(duration_str) if duration_str else None

        chapters_data = data.get("chapters", [])
        chapters = [
            {
                "start_time": float(ch.get("start_time", 0)),
                "end_time": float(ch.get("end_time", 0)),
                "title": ch.get("tags", {}).get("title", f"Chapter {idx + 1}"),
            }
            for idx, ch in enumerate(chapters_data)
        ]
        return duration, chapters
    except (json.JSONDecodeError, subprocess.TimeoutExpired, ValueError, KeyError):
        return None, []
