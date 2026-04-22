"""Plotly figure-building functions for all conference visualisations.

Each function takes pre-computed data (from viz_plots) and returns a go.Figure.
Both the notebook and the plot CLI import from here, eliminating duplication.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from viz_sys_conferences.viz_plots import (
    conference_similarity,
    keyword_heatmap_matrix,
    papers_over_time,
    topic_trends_from_embeddings,
)

_SYMBOLS = ["circle", "square", "diamond", "cross", "triangle-up", "triangle-down", "star", "hexagon"]


def figure_papers_over_time(editions: list[dict]) -> go.Figure:
    """Stacked bar chart of paper counts per conference per year.

    Args:
        editions: Raw edition dicts from load_editions().

    Returns:
        Plotly figure.
    """
    df = papers_over_time(editions)
    fig = px.bar(
        df, x="year", y="paper_count", color="conference",
        barmode="stack",
        title="Papers published per year by conference",
        labels={"paper_count": "Papers", "year": "Year", "conference": "Conference"},
    )
    fig.update_layout(xaxis=dict(dtick=1), hovermode="x unified")
    return fig


def figure_keyword_heatmap(editions: list[dict], top_n: int = 25) -> go.Figure:
    """Heatmap of paper title keyword frequency by year.

    Args:
        editions: Raw edition dicts from load_editions().
        top_n: Number of top keywords to show.

    Returns:
        Plotly figure.
    """
    matrix = keyword_heatmap_matrix(editions, top_n=top_n)
    fig = go.Figure(go.Heatmap(
        z=matrix.values,
        x=[str(y) for y in matrix.columns],
        y=matrix.index.tolist(),
        colorscale="Blues",
        hovertemplate="Keyword: %{y}<br>Year: %{x}<br>Count: %{z}<extra></extra>",
    ))
    fig.update_layout(
        title="Paper title keyword frequency across all conferences",
        xaxis_title="Year",
        yaxis_title="Keyword",
        height=750,
        yaxis=dict(autorange="reversed"),
    )
    return fig


def figure_topic_trends(embeddings_path: Path) -> go.Figure:
    """Line chart of topic frequency over time from pre-computed embeddings.

    Args:
        embeddings_path: Path to the .npz file produced by make embed.

    Returns:
        Plotly figure.
    """
    trends = topic_trends_from_embeddings(embeddings_path)
    topics_ordered = trends["topic"].unique().tolist()
    colors = px.colors.qualitative.Light24[: len(topics_ordered)]

    fig = go.Figure()
    for i, topic in enumerate(topics_ordered):
        df_t = trends[trends["topic"] == topic]
        fig.add_scatter(
            x=df_t["year"], y=df_t["frequency"],
            mode="lines+markers",
            name=topic,
            line=dict(color=colors[i]),
            marker=dict(symbol=_SYMBOLS[i % len(_SYMBOLS)], size=8, color=colors[i]),
        )
    fig.update_layout(
        title="Paper topic frequency over time",
        xaxis=dict(dtick=1, title="Year"),
        yaxis=dict(tickformat=".0%", title="Fraction of papers"),
        hovermode="x unified",
        height=800,
        legend=dict(itemsizing="constant"),
    )
    return fig


def figure_keyword_frequency(
    editions: list[dict],
    keywords: list[str],
    title: str,
) -> go.Figure:
    """Bar chart counting papers whose titles contain any of the given keywords.

    Keywords are matched as whole words (space-padded) case-insensitively.

    Args:
        editions: Raw edition dicts from load_editions().
        keywords: List of keyword strings to search for.
        title: Plot title.

    Returns:
        Plotly figure.
    """
    counts: dict[int, int] = defaultdict(int)
    all_years: set[int] = set()
    for e in editions:
        all_years.add(e["year"])
        for p in e["papers"]:
            padded = " " + p["title"].lower() + " "
            if any(f" {kw} " in padded for kw in keywords):
                counts[e["year"]] += 1

    years = sorted(all_years)
    fig = go.Figure()
    fig.add_bar(x=years, y=[counts[y] for y in years], name="Paper count")
    fig.update_layout(
        title=title,
        xaxis=dict(dtick=1, title="Year"),
        yaxis=dict(title="Paper count"),
        hovermode="x unified",
        height=450,
    )
    return fig


def figure_conference_similarity(editions: list[dict]) -> go.Figure:
    """Heatmap of pairwise Jaccard similarity between conferences.

    Args:
        editions: Raw edition dicts from load_editions().

    Returns:
        Plotly figure.
    """
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
        hovertemplate="%{y} vs %{x}: %{z:.3f}<extra></extra>",
    ))
    fig.update_layout(
        title="Conference topic similarity",
        height=500,
    )
    return fig
