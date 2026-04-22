"""Compute and save paper + topic embeddings using google/embeddinggemma-300m.

Run once to pre-compute embeddings; the notebook then reads from the saved file
without needing to load the model.

Usage:
    uv run embed
    make embed
"""

from __future__ import annotations

from pathlib import Path

import click
import numpy as np
from rich.console import Console

from viz_sys_conferences.viz_data import load_editions

console = Console()

MODEL_NAME = "google/embeddinggemma-300m"
DEFAULT_DATA_DIR = Path("data")
DEFAULT_TOPICS_FILE = Path("config/sosp26_topics.txt")
DEFAULT_OUTPUT = Path("data/embeddings.npz")


@click.command()
@click.option("--data-dir", default=str(DEFAULT_DATA_DIR), type=click.Path(), show_default=True)
@click.option("--topics", default=str(DEFAULT_TOPICS_FILE), type=click.Path(), show_default=True)
@click.option("--output", "-o", default=str(DEFAULT_OUTPUT), type=click.Path(), show_default=True)
def main(data_dir: str, topics: str, output: str) -> None:
    """Encode paper titles and topic names; save embeddings to a .npz file."""
    from sentence_transformers import SentenceTransformer

    editions = load_editions(Path(data_dir))
    topic_list = Path(topics).read_text().strip().splitlines()

    paper_titles: list[str] = []
    paper_years: list[int] = []
    for e in editions:
        for p in e["papers"]:
            paper_titles.append(p["title"])
            paper_years.append(e["year"])

    console.print(f"Loading model [bold]{MODEL_NAME}[/bold] …")
    model = SentenceTransformer(MODEL_NAME)

    console.print(f"Encoding {len(paper_titles)} paper titles …")
    paper_vecs = model.encode_document(paper_titles, show_progress_bar=True, batch_size=64)

    console.print(f"Encoding {len(topic_list)} topics …")
    topic_vecs = model.encode_query(topic_list, show_progress_bar=False)

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        out,
        paper_vecs=paper_vecs,
        topic_vecs=topic_vecs,
        paper_titles=np.array(paper_titles),
        paper_years=np.array(paper_years),
        topics=np.array(topic_list),
    )
    console.print(f"[green]Saved embeddings → {out}[/green]")


if __name__ == "__main__":
    main()
