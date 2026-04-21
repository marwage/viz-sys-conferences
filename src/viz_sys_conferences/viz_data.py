"""Load crawled conference data from JSON files into plain dicts."""

from __future__ import annotations

import json
from pathlib import Path


def load_editions(data_dir: Path = Path("data")) -> list[dict]:
    """Return all crawled conference editions as plain dicts, sorted by (conference, year).

    Args:
        data_dir: Directory containing the per-edition JSON files.

    Returns:
        List of edition dicts, each with keys: conference, year, url,
        crawled_at, papers.
    """
    editions = []
    for path in sorted(data_dir.glob("*.json")):
        data = json.loads(path.read_text())
        if "conference" in data and "year" in data:
            editions.append(data)
    editions.sort(key=lambda e: (e["conference"], e["year"]))
    return editions
