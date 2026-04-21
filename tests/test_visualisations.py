"""Tests for visualisation data-preparation functions.

All tests run fully offline — no API calls, no Jupyter kernel, no Plotly.
The real data in data/ is used for domain-property tests; synthetic data for unit tests.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from viz_sys_conferences.viz_data import load_editions
from viz_sys_conferences.viz_plots import (
    N_CLUSTERS,
    build_cluster_data,
    conference_similarity,
    get_cluster_labels,
    keyword_heatmap_matrix,
    keyword_trends,
    papers_over_time,
)

DATA_DIR = Path(__file__).parent.parent / "data"


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def editions() -> list[dict]:
    return load_editions(DATA_DIR)


@pytest.fixture
def tiny_editions() -> list[dict]:
    """Minimal synthetic editions for fast, isolated tests."""
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


# ── build_cluster_data ────────────────────────────────────────────────────────


def test_cluster_count(tiny_editions):
    n_papers = sum(len(e["papers"]) for e in tiny_editions)
    titles, conf_years, cluster_ids, matrix = build_cluster_data(tiny_editions, n_clusters=3)
    assert len(titles) == len(conf_years) == len(cluster_ids) == n_papers


def test_cluster_all_titles_assigned(tiny_editions):
    titles, conf_years, cluster_ids, matrix = build_cluster_data(tiny_editions, n_clusters=3)
    assert all(isinstance(c, int) for c in cluster_ids)
    assert len(set(cluster_ids)) == 3


def test_cluster_real_data_n_clusters(editions):
    titles, conf_years, cluster_ids, matrix = build_cluster_data(editions)
    assert len(set(cluster_ids)) == N_CLUSTERS


def test_cluster_matrix_shape(editions):
    titles, conf_years, cluster_ids, matrix = build_cluster_data(editions)
    assert matrix.shape[0] == len(titles)
    assert matrix.shape[1] <= 5000


# ── get_cluster_labels (with cache) ──────────────────────────────────────────


def test_cluster_label_cache_write_and_read():
    titles = ["Fast storage system", "Key-value store", "Network scheduling"]
    cluster_ids = [0, 0, 1]
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Storage Systems")]

    with tempfile.TemporaryDirectory() as tmp:
        cache_path = Path(tmp) / "labels.json"
        with patch("anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = mock_response
            labels1 = get_cluster_labels(titles, cluster_ids, cache_path=cache_path)
            assert cache_path.exists()
            assert instance.messages.create.call_count == 2
            labels2 = get_cluster_labels(titles, cluster_ids, cache_path=cache_path)
            assert instance.messages.create.call_count == 2  # cache hit
        assert labels1 == labels2
        assert set(labels1.keys()) == {0, 1}


def test_cluster_label_cache_keys_are_ints():
    titles = ["Operating system kernel", "Thread scheduling"]
    cluster_ids = [0, 0]
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="OS Kernel")]

    with tempfile.TemporaryDirectory() as tmp:
        cache_path = Path(tmp) / "labels.json"
        with patch("anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = mock_response
            labels = get_cluster_labels(titles, cluster_ids, cache_path=cache_path)
        assert all(isinstance(k, int) for k in labels)


# ── keyword_trends ────────────────────────────────────────────────────────────


def test_keyword_trends_columns(editions):
    df = keyword_trends(editions)
    assert set(df.columns) == {"year", "topic", "frequency"}


def test_keyword_trends_frequency_range(editions):
    df = keyword_trends(editions)
    assert df["frequency"].between(0.0, 1.0).all()


def test_keyword_trends_one_row_per_year_per_topic(editions):
    from viz_sys_conferences.viz_plots import KEYWORD_GROUPS

    df = keyword_trends(editions)
    n_years = df["year"].nunique()
    n_topics = len(KEYWORD_GROUPS)
    assert len(df) == n_years * n_topics


def test_keyword_trends_ml_rises_over_time(editions):
    """ML/AI frequency should be higher in 2022–2025 than 2006–2010."""
    df = keyword_trends(editions)
    ml = df[df["topic"] == "ML / AI"]
    early = ml[ml["year"].between(2006, 2010)]["frequency"].mean()
    late = ml[ml["year"].between(2022, 2025)]["frequency"].mean()
    assert late > early, f"Expected ML to rise: early={early:.3f}, late={late:.3f}"


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
