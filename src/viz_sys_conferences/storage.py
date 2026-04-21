from __future__ import annotations

from pathlib import Path

from viz_sys_conferences.models import ConferenceEdition


def save_edition(edition: ConferenceEdition, output_dir: Path) -> Path:
    """Save one edition as a pretty-printed JSON file.

    Args:
        edition: The conference edition to save.
        output_dir: Directory to write the file into.

    Returns:
        Path to the written file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{edition.conference}_{edition.year}.json"
    path.write_text(edition.model_dump_json(indent=2))
    return path
