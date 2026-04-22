"""Generate all visualisation plots as SVG files.

Usage:
    uv run plot
    make plots
"""

from __future__ import annotations

from pathlib import Path

import click
import plotly.graph_objects as go
from rich.console import Console

from viz_sys_conferences.viz_data import load_editions
from viz_sys_conferences.viz_figures import (
    figure_conference_similarity,
    figure_keyword_frequency,
    figure_keyword_heatmap,
    figure_papers_over_time,
    figure_topic_trends,
)

console = Console()

DEFAULT_DATA_DIR = Path("data")
DEFAULT_OUTPUT_DIR = Path("plots")
DEFAULT_EMBEDDINGS = Path("data/embeddings.npz")
DEFAULT_CONFIG_DIR = Path("config")


def _save(fig: go.Figure, path: Path, width: int = 1200, height: int | None = None) -> None:
    h = height or fig.layout.height or 600
    fig.write_image(str(path), format="svg", width=width, height=h)
    console.print(f"[green]✓[/green] {path}")


@click.command()
@click.option("--data-dir", default=str(DEFAULT_DATA_DIR), type=click.Path(), show_default=True)
@click.option("--embeddings", default=str(DEFAULT_EMBEDDINGS), type=click.Path(), show_default=True)
@click.option("--config-dir", default=str(DEFAULT_CONFIG_DIR), type=click.Path(), show_default=True)
@click.option("--output", "-o", default=str(DEFAULT_OUTPUT_DIR), type=click.Path(), show_default=True)
@click.option("--width", default=1200, type=int, show_default=True, help="SVG width in pixels.")
def main(data_dir: str, embeddings: str, config_dir: str, output: str, width: int) -> None:
    """Render all conference visualisation plots to SVG files."""
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    cfg = Path(config_dir)

    editions = load_editions(Path(data_dir))
    console.print(f"Loaded {len(editions)} editions")

    _save(figure_papers_over_time(editions), out / "1_papers_over_time.svg", width=width)
    _save(figure_keyword_heatmap(editions), out / "2_keyword_heatmap.svg", width=width, height=750)

    emb_path = Path(embeddings)
    if emb_path.exists():
        _save(figure_topic_trends(emb_path), out / "3_topic_trends.svg", width=width, height=800)
    else:
        console.print(f"[yellow]Skipping topic trends — {emb_path} not found. Run make embed first.[/yellow]")

    _save(
        figure_keyword_frequency(
            editions,
            keywords=["determinism", "deterministic"],
            title="Frequency of determinism / deterministic in paper titles",
        ),
        out / "4_determinism.svg", width=width, height=450,
    )

    ai_keywords = [kw.strip() for kw in (cfg / "ai_keywords.txt").read_text().splitlines() if kw.strip()]
    _save(
        figure_keyword_frequency(editions, keywords=ai_keywords, title="AI-related keywords in paper titles"),
        out / "4b_ai_keywords.svg", width=width, height=450,
    )

    _save(figure_conference_similarity(editions), out / "5_conference_similarity.svg", width=width, height=500)

    console.print(f"\n[bold]Done.[/bold] SVGs written to {out}/")


if __name__ == "__main__":
    main()
