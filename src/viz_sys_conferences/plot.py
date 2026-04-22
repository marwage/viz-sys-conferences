"""Generate all visualisation plots as SVG files.

Usage:
    uv run plot
    make plots
"""

from __future__ import annotations

from pathlib import Path

import click
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from rich.console import Console

from viz_sys_conferences.viz_data import load_editions
from viz_sys_conferences.viz_plots import (
    conference_similarity,
    keyword_heatmap_matrix,
    papers_over_time,
    topic_trends_from_embeddings,
)

console = Console()

DEFAULT_DATA_DIR = Path("data")
DEFAULT_OUTPUT_DIR = Path("plots")
DEFAULT_EMBEDDINGS = Path("data/embeddings.npz")


def _save(fig: go.Figure, path: Path, width: int = 1200, height: int | None = None) -> None:
    h = height or fig.layout.height or 600
    fig.write_image(str(path), format="svg", width=width, height=h)
    console.print(f"[green]✓[/green] {path}")


@click.command()
@click.option("--data-dir", default=str(DEFAULT_DATA_DIR), type=click.Path(), show_default=True)
@click.option("--embeddings", default=str(DEFAULT_EMBEDDINGS), type=click.Path(), show_default=True)
@click.option("--output", "-o", default=str(DEFAULT_OUTPUT_DIR), type=click.Path(), show_default=True)
@click.option("--width", default=1200, type=int, show_default=True, help="SVG width in pixels.")
def main(data_dir: str, embeddings: str, output: str, width: int) -> None:
    """Render all conference visualisation plots to SVG files."""
    data_path = Path(data_dir)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)

    editions = load_editions(data_path)
    console.print(f"Loaded {len(editions)} editions")

    # 1 · Papers over time
    df = papers_over_time(editions)
    fig = px.bar(
        df, x="year", y="paper_count", color="conference",
        barmode="stack",
        title="Papers published per year by conference",
        labels={"paper_count": "Papers", "year": "Year", "conference": "Conference"},
    )
    fig.update_layout(xaxis=dict(dtick=1), hovermode="x unified")
    _save(fig, out / "1_papers_over_time.svg", width=width)

    # 2 · Keyword heatmap
    matrix = keyword_heatmap_matrix(editions, top_n=25)
    fig = go.Figure(go.Heatmap(
        z=matrix.values,
        x=[str(y) for y in matrix.columns],
        y=matrix.index.tolist(),
        colorscale="Blues",
    ))
    fig.update_layout(
        title="Paper title keyword frequency across all conferences",
        xaxis_title="Year",
        yaxis_title="Keyword",
        height=750,
        yaxis=dict(autorange="reversed"),
    )
    _save(fig, out / "2_keyword_heatmap.svg", width=width, height=750)

    # 3 · Topic trend lines
    emb_path = Path(embeddings)
    if not emb_path.exists():
        console.print(f"[yellow]Skipping topic trends — {emb_path} not found. Run make embed first.[/yellow]")
    else:
        trends = topic_trends_from_embeddings(emb_path)
        topics_ordered = trends["topic"].unique().tolist()
        colors = px.colors.qualitative.Light24[: len(topics_ordered)]
        symbols = ["circle", "square", "diamond", "cross", "triangle-up", "triangle-down", "star", "hexagon"]

        fig = go.Figure()
        for i, topic in enumerate(topics_ordered):
            df_t = trends[trends["topic"] == topic]
            fig.add_scatter(
                x=df_t["year"], y=df_t["frequency"],
                mode="lines+markers",
                name=topic,
                line=dict(color=colors[i]),
                marker=dict(symbol=symbols[i % len(symbols)], size=8, color=colors[i]),
            )
        fig.update_layout(
            title="Paper topic frequency over time",
            xaxis=dict(dtick=1, title="Year"),
            yaxis=dict(tickformat=".0%", title="Fraction of papers"),
            hovermode="x unified",
            height=800,
            legend=dict(itemsizing="constant"),
        )
        _save(fig, out / "3_topic_trends.svg", width=width, height=800)

    # 4 · Determinism
    from collections import defaultdict
    counts_by_year: dict[int, int] = defaultdict(int)
    for e in editions:
        for p in e["papers"]:
            if "determinis" in p["title"].lower():
                counts_by_year[e["year"]] += 1

    years = sorted(counts_by_year)
    fig = go.Figure()
    fig.add_bar(x=years, y=[counts_by_year[y] for y in years], name="Paper count")
    fig.update_layout(
        title="Frequency of determinism / deterministic in paper titles",
        xaxis=dict(dtick=1, title="Year"),
        yaxis=dict(title="Paper count"),
        height=450,
    )
    _save(fig, out / "4_determinism.svg", width=width, height=450)

    # 5 · Conference similarity
    sim = conference_similarity(editions)
    confs = sim.index.tolist()
    fig = go.Figure(go.Heatmap(
        z=sim.values,
        x=confs,
        y=confs,
        colorscale="Viridis",
        zmin=0, zmax=1,
        text=np.round(sim.values, 2),
        texttemplate="%{text}",
    ))
    fig.update_layout(
        title="Conference topic similarity (Jaccard of top-200 paper title words)",
        height=500,
    )
    _save(fig, out / "5_conference_similarity.svg", width=width, height=500)

    console.print(f"\n[bold]Done.[/bold] SVGs written to {out}/")


if __name__ == "__main__":
    main()
