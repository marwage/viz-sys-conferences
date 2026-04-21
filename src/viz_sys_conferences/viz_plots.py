"""Pure data-preparation functions for all conference visualisations.

Each function takes the edition list from viz_data.load_editions() and returns
a plain Python structure (DataFrame, list, dict) that the notebook then passes
to Plotly. Keeping Plotly imports out of this module makes it fully unit-testable.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

logger = logging.getLogger(__name__)

# ── stopwords ────────────────────────────────────────────────────────────────

_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "for",
    "of",
    "in",
    "on",
    "at",
    "to",
    "with",
    "from",
    "by",
    "is",
    "are",
    "be",
    "as",
    "it",
    "its",
    "this",
    "that",
    "we",
    "our",
    "their",
    "via",
    "using",
    "based",
    "towards",
    "toward",
    "large",
    "scale",
    "high",
    "fast",
    "new",
    "efficient",
    "case",
    "study",
    "keynote",
    "address",
    "session",
    "talk",
    "invited",
    "workshop",
    "panel",
    "award",
    "joint",
    # conference names
    "osdi",
    "nsdi",
    "atc",
    "sosp",
    "eurosys",
    "usenix",
    "ieee",
    "acm",
    # domain-generic — appear in almost every paper/session
    "system",
    "systems",
    "one",
    "two",
    "part",
    "rest",
    "approach",
    "paper",
    "work",
    "problem",
    "method",
    "show",
    "use",
    "used",
    "make",
    "can",
    "also",
    "well",
    "first",
    "second",
    "time",
    "data",
    "design",
    "support",
    "provide",
    "improve",
    "performance",
    "result",
    "results",
    "existing",
}

# ── keyword topic groups for trend-line plot ─────────────────────────────────

KEYWORD_GROUPS: dict[str, list[str]] = {
    "ML / AI": [
        "machine learning",
        "deep learning",
        "neural",
        "llm",
        "gpt",
        "inference",
        "training",
        "model",
        "transformer",
        "gpu",
    ],
    "Cloud": [
        "cloud",
        "serverless",
        "faas",
        "datacenter",
        "data center",
        "container",
        "kubernetes",
        "microservice",
        "saas",
    ],
    "Storage": [
        "storage",
        "file system",
        "filesystem",
        "database",
        "key-value",
        "kv",
        "flash",
        "ssd",
        "nvm",
        "persistent",
    ],
    "Networking": [
        "network",
        "rdma",
        "rpc",
        "tcp",
        "congestion",
        "routing",
        "switch",
        "nic",
        "smartnic",
        "p4",
    ],
    "Security": [
        "security",
        "privacy",
        "sgx",
        "tee",
        "trusted",
        "attack",
        "exploit",
        "vulnerability",
        "isolation",
        "enclave",
    ],
    "Distributed Systems": [
        "distributed",
        "consensus",
        "paxos",
        "raft",
        "replication",
        "fault tolerance",
        "byzantine",
        "consistency",
        "transaction",
    ],
    "Verification": [
        "verification",
        "formal",
        "proof",
        "correctness",
        "model checking",
        "specification",
        "symbolic",
    ],
    "OS / Kernel": [
        "kernel",
        "operating system",
        "os",
        "process",
        "thread",
        "scheduler",
        "scheduling",
        "memory management",
        "hypervisor",
        "virtualization",
        "virtualisation",
        "vm",
    ],
    "Hardware": [
        "fpga",
        "accelerator",
        "hardware",
        "cpu",
        "cache",
        "architecture",
        "memory",
        "dram",
        "cxl",
    ],
    "Bugs / Testing": [
        "bug",
        "fuzzing",
        "fuzz",
        "test",
        "debugging",
        "race",
        "concurrency",
        "static analysis",
    ],
}


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
        paper_count = sum(len(s["papers"]) for s in e["sessions"])
        rows.append({"conference": e["conference"], "year": e["year"], "paper_count": paper_count})
    return pd.DataFrame(rows)


# ── 2 · session topic heatmap ────────────────────────────────────────────────


def session_heatmap_matrix(
    editions: list[dict],
    top_n: int = 40,
    conference: str | None = None,
) -> pd.DataFrame:
    """Build a keyword × year count matrix from session titles.

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
        for s in e["sessions"]:
            words = _tokenise(s["title"])
            counts[year].update(words)

    all_years = sorted(counts)
    total: Counter = Counter()
    for c in counts.values():
        total.update(c)

    top_words = [w for w, _ in total.most_common(top_n * 2) if w not in _STOPWORDS][:top_n]

    matrix = pd.DataFrame(
        {year: [counts[year].get(w, 0) for w in top_words] for year in all_years},
        index=top_words,
    )
    return matrix


# ── 3 · paper clustering ─────────────────────────────────────────────────────

N_CLUSTERS = 20


def build_cluster_data(
    editions: list[dict],
    n_clusters: int = N_CLUSTERS,
) -> tuple[list[str], list[str], list[int], np.ndarray]:
    """Vectorise all paper titles with TF-IDF and cluster with KMeans.

    Args:
        editions: Raw edition dicts from load_editions().
        n_clusters: Number of KMeans clusters. Capped at the number of papers.

    Returns:
        Tuple of (titles, conference_years, cluster_ids, tfidf_matrix) where:
        - titles: list of paper title strings
        - conference_years: list of "{CONF} {year}" strings for each paper
        - cluster_ids: list of integer cluster assignments
        - tfidf_matrix: sparse matrix, shape (n_papers, n_features)
    """
    titles: list[str] = []
    conf_years: list[str] = []
    for e in editions:
        label = f"{e['conference']} {e['year']}"
        for s in e["sessions"]:
            for p in s["papers"]:
                titles.append(p["title"])
                conf_years.append(label)

    k = min(n_clusters, len(titles))
    vectoriser = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), stop_words="english")
    matrix = vectoriser.fit_transform(titles)
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    cluster_ids = kmeans.fit_predict(matrix).tolist()
    return titles, conf_years, cluster_ids, matrix


def get_cluster_labels(
    titles: list[str],
    cluster_ids: list[int],
    cache_path: Path = Path("data/cluster_labels.json"),
) -> dict[int, str]:
    """Return {cluster_id: topic_label}, using cache if available.

    Calls Claude claude-haiku-4-5 for each cluster if the cache does not exist.

    Args:
        titles: Paper title strings.
        cluster_ids: Cluster assignment for each title.
        cache_path: JSON file to read/write cached labels.

    Returns:
        Dict mapping cluster id (int) to a 2–4 word topic label (str).
    """
    if cache_path.exists():
        raw = json.loads(cache_path.read_text())
        return {int(k): v for k, v in raw.items()}

    import anthropic

    client = anthropic.Anthropic()

    # Group titles per cluster
    clusters: dict[int, list[str]] = defaultdict(list)
    for title, cid in zip(titles, cluster_ids, strict=True):
        clusters[cid].append(title)

    labels: dict[int, str] = {}
    for cid in sorted(clusters):
        sample = clusters[cid][:15]
        prompt = (
            "Below are titles of systems research papers that have been grouped "
            "into a cluster by a topic model.\n\n"
            + "\n".join(f"- {t}" for t in sample)
            + "\n\nGive this cluster a concise 2–4 word research topic label. "
            "Reply with only the label, nothing else."
        )
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}],
        )
        label = response.content[0].text.strip()
        labels[cid] = label
        logger.info("Cluster %d → %s", cid, label)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({str(k): v for k, v in labels.items()}, indent=2))
    return labels


def umap_projection(matrix) -> np.ndarray:
    """Project a TF-IDF sparse matrix to 2-D with UMAP.

    Args:
        matrix: Sparse TF-IDF matrix, shape (n_samples, n_features).

    Returns:
        2-D numpy array, shape (n_samples, 2).
    """
    from umap import UMAP

    dense = normalize(matrix, norm="l2")
    reducer = UMAP(n_components=2, random_state=42, n_neighbors=15, min_dist=0.1)
    return reducer.fit_transform(dense)


# ── 4 · keyword trend lines ──────────────────────────────────────────────────


def keyword_trends(editions: list[dict]) -> pd.DataFrame:
    """Compute per-year normalised frequency for each keyword group.

    Frequency = (titles containing ≥1 keyword from group) / (total titles that year).

    Args:
        editions: Raw edition dicts from load_editions().

    Returns:
        DataFrame with columns: year, topic, frequency.
    """
    # Collect all titles per year
    titles_by_year: dict[int, list[str]] = defaultdict(list)
    for e in editions:
        year = e["year"]
        for s in e["sessions"]:
            for p in s["papers"]:
                titles_by_year[year].append(p["title"].lower())
            titles_by_year[year].append(s["title"].lower())

    rows = []
    for year in sorted(titles_by_year):
        all_titles = titles_by_year[year]
        n = len(all_titles)
        for topic, keywords in KEYWORD_GROUPS.items():
            hits = sum(1 for t in all_titles if any(kw in t for kw in keywords))
            rows.append({"year": year, "topic": topic, "frequency": hits / n if n else 0.0})
    return pd.DataFrame(rows)


# ── 5 · session sunburst ─────────────────────────────────────────────────────


def sunburst_data(editions: list[dict]) -> list[dict]:
    """Build records for a conference → year → session sunburst plot.

    Args:
        editions: Raw edition dicts from load_editions().

    Returns:
        List of dicts with keys: conference, year, session, paper_count.
        Only sessions with paper_count > 0 are included.
    """
    rows = []
    for e in editions:
        for s in e["sessions"]:
            count = len(s["papers"])
            if count > 0:
                rows.append(
                    {
                        "conference": e["conference"],
                        "year": e["year"],
                        "session": s["title"],
                        "paper_count": count,
                    }
                )
    return rows


# ── 6 · conference similarity ────────────────────────────────────────────────


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

    word_sets: dict[str, set[str]] = defaultdict(Counter)
    for e in editions:
        conf = e["conference"]
        for s in e["sessions"]:
            word_sets[conf].update(_tokenise(s["title"]))
            for p in s["papers"]:
                word_sets[conf].update(_tokenise(p["title"]))

    # Take top-N words per conference as a set
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


def _tokenise(text: str) -> list[str]:
    """Lowercase, strip punctuation, return non-stopword tokens of length ≥ 3."""
    tokens = re.findall(r"[a-z]{3,}", text.lower())
    return [t for t in tokens if t not in _STOPWORDS]
