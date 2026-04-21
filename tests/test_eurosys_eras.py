"""Tests for EuroSys parsing across different HTML eras."""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from viz_sys_conferences.crawlers.eurosys import EuroSysCrawler

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def crawler() -> EuroSysCrawler:
    return EuroSysCrawler()


def _load(name: str) -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / f"{name}.html").read_text(), "lxml")


# ── 2025: table.pap (3-column) ────────────────────────────────────────────────


def test_2025_session_count(crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(_load("eurosys_2025"))
    assert len(sessions) >= 15


def test_2025_papers_extracted(crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(_load("eurosys_2025"))
    all_papers = [p for s in sessions for p in s.papers]
    assert len(all_papers) >= 40


def test_2025_authors_extracted(crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(_load("eurosys_2025"))
    all_papers = [p for s in sessions for p in s.papers]
    assert any(p.authors for p in all_papers)


# ── 2023/2024: td[id] + ul.sch ────────────────────────────────────────────────


def test_2024_session_count(crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(_load("eurosys_2024"))
    assert len(sessions) >= 10


def test_2024_papers_extracted(crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(_load("eurosys_2024"))
    all_papers = [p for s in sessions for p in s.papers]
    assert len(all_papers) >= 30


def test_2024_authors_extracted(crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(_load("eurosys_2024"))
    all_papers = [p for s in sessions for p in s.papers]
    assert any(p.authors for p in all_papers)


def test_2023_session_count(crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(_load("eurosys_2023"))
    assert len(sessions) >= 10


def test_2023_papers_non_empty(crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(_load("eurosys_2023"))
    for s in sessions:
        assert s.papers, f"Session '{s.title}' has no papers"


# ── 2022: h5 + ul > li ────────────────────────────────────────────────────────


def test_2022_session_count(crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(_load("eurosys_2022"))
    assert len(sessions) >= 8


def test_2022_papers_extracted(crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(_load("eurosys_2022"))
    all_papers = [p for s in sessions for p in s.papers]
    assert len(all_papers) >= 30


def test_2022_session_titles_no_time(crawler: EuroSysCrawler):
    import re

    sessions = crawler.parse_sessions(_load("eurosys_2022"))
    for s in sessions:
        assert not re.search(r"\d+:\d+", s.title), f"Time in title: {s.title!r}"


# ── 2019: h6 + div ────────────────────────────────────────────────────────────


def test_2019_session_count(crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(_load("eurosys_2019"))
    assert len(sessions) >= 8


def test_2019_papers_extracted(crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(_load("eurosys_2019"))
    all_papers = [p for s in sessions for p in s.papers]
    assert len(all_papers) >= 20


def test_2019_no_non_session_titles(crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(_load("eurosys_2019"))
    skip_words = {"registration", "coffee", "break", "lunch", "dinner", "poster"}
    for s in sessions:
        assert not any(w in s.title.lower() for w in skip_words), (
            f"Non-session title leaked: {s.title!r}"
        )
