"""Tests for visualisation data-preparation functions.

All tests run fully offline — no API calls, no Jupyter kernel, no Plotly.
The real data in data/ is used for domain-property tests; synthetic data for unit tests.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from viz_sys_conferences.viz_data import load_editions
from viz_sys_conferences.viz_plots import (
    conference_similarity,
    keyword_heatmap_matrix,
    papers_over_time,
    topic_trends_from_embeddings,
)

DATA_DIR = Path(__file__).parent.parent / "data"
EMBEDDINGS = DATA_DIR / "embeddings.npz"


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def editions() -> list[dict]:
    return load_editions(DATA_DIR)


@pytest.fixture
def tiny_editions() -> list[dict]:
    return [
        {
            "conference": "FOO",
            "year": 2020,
            "papers": [
                {
                    "title": "Fast Neural Network Inference",
                    "authors": [],
                    "abstract": None,
                    "award": None,
                },
                {
                    "title": "Distributed Training at Scale",
                    "authors": [],
                    "abstract": None,
                    "award": None,
                },
                {"title": "Key-Value Store Design", "authors": [], "abstract": None, "award": None},
            ],
        },
        {
            "conference": "BAR",
            "year": 2021,
            "papers": [
                {"title": "TCP Congestion Control", "authors": [], "abstract": None, "award": None},
                {"title": "RDMA over Ethernet", "authors": [], "abstract": None, "award": None},
            ],
        },
        {
            "conference": "FOO",
            "year": 2021,
            "papers": [
                {"title": "GPU Memory Management", "authors": [], "abstract": None, "award": None},
                {
                    "title": "LLM Inference Optimisation",
                    "authors": [],
                    "abstract": None,
                    "award": None,
                },
            ],
        },
    ]


# ── load_editions ─────────────────────────────────────────────────────────────


def test_load_editions_returns_list(editions):
    assert isinstance(editions, list)
    assert len(editions) > 0


def test_load_editions_required_keys(editions):
    for e in editions:
        assert "conference" in e
        assert "year" in e
        assert "papers" in e


def test_load_editions_sorted(editions):
    pairs = [(e["conference"], e["year"]) for e in editions]
    assert pairs == sorted(pairs)


# ── papers_over_time ──────────────────────────────────────────────────────────


def test_papers_over_time_columns(tiny_editions):
    df = papers_over_time(tiny_editions)
    assert set(df.columns) == {"conference", "year", "paper_count"}


def test_papers_over_time_one_row_per_edition(tiny_editions):
    df = papers_over_time(tiny_editions)
    assert len(df) == len(tiny_editions)


def test_papers_over_time_non_negative(tiny_editions):
    df = papers_over_time(tiny_editions)
    assert (df["paper_count"] >= 0).all()


def test_papers_over_time_correct_counts(tiny_editions):
    df = papers_over_time(tiny_editions)
    foo_2020 = df[(df["conference"] == "FOO") & (df["year"] == 2020)]["paper_count"].iloc[0]
    assert foo_2020 == 3


def test_papers_over_time_year_dtype(editions):
    df = papers_over_time(editions)
    assert all(isinstance(y, (int, np.integer)) for y in df["year"])


# ── keyword_heatmap_matrix ────────────────────────────────────────────────────


def test_heatmap_matrix_shape(tiny_editions):
    matrix = keyword_heatmap_matrix(tiny_editions, top_n=5)
    assert matrix.shape[0] <= 5
    assert matrix.shape[1] == len({e["year"] for e in tiny_editions})


def test_heatmap_matrix_non_negative(tiny_editions):
    matrix = keyword_heatmap_matrix(tiny_editions, top_n=10)
    assert (matrix.values >= 0).all()


def test_heatmap_matrix_year_columns(tiny_editions):
    matrix = keyword_heatmap_matrix(tiny_editions, top_n=5)
    for col in matrix.columns:
        assert isinstance(col, int)


def test_heatmap_matrix_no_stopwords(editions):
    matrix = keyword_heatmap_matrix(editions, top_n=40)
    stopwords = {"the", "and", "for", "with", "session", "a", "an"}
    for word in matrix.index:
        assert word not in stopwords, f"Stopword '{word}' in heatmap index"


def test_heatmap_matrix_conference_filter(editions):
    osdi_matrix = keyword_heatmap_matrix(editions, conference="OSDI")
    osdi_years = {e["year"] for e in editions if e["conference"] == "OSDI"}
    assert set(osdi_matrix.columns) == osdi_years


# ── topic_trends_from_embeddings ──────────────────────────────────────────────


@pytest.mark.skipif(not EMBEDDINGS.exists(), reason="embeddings.npz not present — run make embed")
def test_topic_trends_columns():
    df = topic_trends_from_embeddings(EMBEDDINGS)
    assert set(df.columns) == {"year", "topic", "count", "frequency"}


@pytest.mark.skipif(not EMBEDDINGS.exists(), reason="embeddings.npz not present — run make embed")
def test_topic_trends_frequency_range():
    df = topic_trends_from_embeddings(EMBEDDINGS)
    assert df["frequency"].between(0.0, 1.0).all()


@pytest.mark.skipif(not EMBEDDINGS.exists(), reason="embeddings.npz not present — run make embed")
def test_topic_trends_all_years_covered(editions):
    df = topic_trends_from_embeddings(EMBEDDINGS)
    edition_years = {e["year"] for e in editions}
    assert edition_years.issubset(set(df["year"]))


# ── conference_similarity ─────────────────────────────────────────────────────


def test_similarity_matrix_shape(editions):
    df = conference_similarity(editions)
    n = df.shape[0]
    assert df.shape == (n, n)
    assert set(df.index) == set(df.columns)


def test_similarity_matrix_diagonal(editions):
    df = conference_similarity(editions)
    for conf in df.index:
        assert df.loc[conf, conf] == pytest.approx(1.0)


def test_similarity_matrix_symmetric(editions):
    df = conference_similarity(editions)
    for ci in df.index:
        for cj in df.columns:
            assert df.loc[ci, cj] == pytest.approx(df.loc[cj, ci])


def test_similarity_matrix_off_diagonal_range(editions):
    df = conference_similarity(editions)
    for ci in df.index:
        for cj in df.columns:
            if ci != cj:
                assert 0.0 <= df.loc[ci, cj] < 1.0


def test_similarity_matrix_year_filter(editions):
    full = conference_similarity(editions)
    recent = conference_similarity(editions, year_range=(2020, 2026))
    assert set(full.index) == set(recent.index)
