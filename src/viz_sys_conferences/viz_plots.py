"""Pure data-preparation functions for all conference visualisations.

Each function takes the edition list from viz_data.load_editions() and returns
a plain Python structure (DataFrame, list, dict) that the notebook then passes
to Plotly. Keeping Plotly imports out of this module makes it fully unit-testable.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

_STOPWORDS_FILE = Path(__file__).parent.parent.parent / "config" / "heatmap_stopwords.txt"
_STOPWORDS: set[str] = set(_STOPWORDS_FILE.read_text().splitlines())


# ── 1 · papers over time ─────────────────────────────────────────────────────


def papers_over_time(editions: list[dict]) -> pd.DataFrame:
    """Build a DataFrame of paper counts per conference per year.

    Args:
        editions: Raw edition dicts from load_editions().

    Returns:
        DataFrame with columns: conference, year, paper_count.
    """
    rows = []
    for e in editions:
        rows.append(
            {"conference": e["conference"], "year": e["year"], "paper_count": len(e["papers"])}
        )
    return pd.DataFrame(rows)


# ── 2 · paper title keyword heatmap ──────────────────────────────────────────


def keyword_heatmap_matrix(
    editions: list[dict],
    top_n: int = 40,
    conference: str | None = None,
) -> pd.DataFrame:
    """Build a keyword × year count matrix from paper titles.

    Args:
        editions: Raw edition dicts from load_editions().
        top_n: Number of top keywords to include as rows.
        conference: If given, restrict to that conference only.

    Returns:
        DataFrame indexed by keyword, columns are years (ints), values are counts.
    """
    if conference:
        editions = [e for e in editions if e["conference"] == conference]

    counts: dict[int, Counter] = defaultdict(Counter)
    for e in editions:
        year = e["year"]
        for p in e["papers"]:
            counts[year].update(_words(p["title"]))

    all_years = sorted(counts)
    total: Counter = Counter()
    for c in counts.values():
        total.update(c)

    top_words = [w for w, _ in total.most_common(top_n * 2) if w not in _STOPWORDS][:top_n]

    return pd.DataFrame(
        {year: [counts[year].get(w, 0) for w in top_words] for year in all_years},
        index=top_words,
    )


# ── 3 · topic trend lines ────────────────────────────────────────────────────


def topic_trends_from_embeddings(
    embeddings_path: Path = Path("data/embeddings.npz"),
) -> pd.DataFrame:
    """Load pre-computed embeddings and assign papers to topics by cosine similarity.

    Args:
        embeddings_path: Path to the .npz file produced by `make embed`.

    Returns:
        DataFrame with columns: year, topic, count, frequency.
    """
    from sklearn.metrics.pairwise import cosine_similarity

    data = np.load(embeddings_path, allow_pickle=True)
    paper_vecs = data["paper_vecs"]
    topic_vecs = data["topic_vecs"]
    paper_years = data["paper_years"].tolist()
    topics = data["topics"].tolist()

    sims = cosine_similarity(paper_vecs, topic_vecs)
    assignments = sims.argmax(axis=1)

    rows = [
        {"year": year, "topic": topics[cid]}
        for year, cid in zip(paper_years, assignments, strict=True)
    ]
    df = pd.DataFrame(rows)
    totals = df.groupby("year")["topic"].count().rename("total")
    counts = df.groupby(["year", "topic"]).size().reset_index(name="count")
    counts = counts.join(totals, on="year")
    counts["frequency"] = counts["count"] / counts["total"]
    return counts[["year", "topic", "count", "frequency"]]


# ── 4 · conference similarity ────────────────────────────────────────────────


def conference_similarity(
    editions: list[dict],
    top_n: int = 200,
    year_range: tuple[int, int] | None = None,
) -> pd.DataFrame:
    """Compute pairwise Jaccard similarity of top title words between conferences.

    Args:
        editions: Raw edition dicts from load_editions().
        top_n: Number of top words per conference to include in the word set.
        year_range: Optional (min_year, max_year) inclusive filter.

    Returns:
        Symmetric DataFrame of shape (n_conferences, n_conferences) with Jaccard
        similarity values. Diagonal is 1.0.
    """
    if year_range:
        lo, hi = year_range
        editions = [e for e in editions if lo <= e["year"] <= hi]

    word_sets: dict[str, Counter] = defaultdict(Counter)
    for e in editions:
        conf = e["conference"]
        for p in e["papers"]:
            word_sets[conf].update(_words(p["title"]))

    top_sets: dict[str, set[str]] = {
        conf: {w for w, _ in counter.most_common(top_n)} for conf, counter in word_sets.items()
    }

    conferences = sorted(top_sets)
    n = len(conferences)
    matrix = np.zeros((n, n))
    for i, ci in enumerate(conferences):
        for j, cj in enumerate(conferences):
            a, b = top_sets[ci], top_sets[cj]
            inter = len(a & b)
            union = len(a | b)
            matrix[i, j] = inter / union if union else 0.0

    return pd.DataFrame(matrix, index=conferences, columns=conferences)


# ── helpers ──────────────────────────────────────────────────────────────────


def _words(text: str) -> list[str]:
    """Extract lowercase words of length ≥ 3, excluding stopwords."""
    return [w for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in _STOPWORDS]
