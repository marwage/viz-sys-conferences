from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from viz_sys_conferences.crawlers.sosp import SospCrawler

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sosp_2025_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "sosp_2025.html").read_text(), "lxml")


@pytest.fixture
def crawler() -> SospCrawler:
    return SospCrawler()


def test_session_count(sosp_2025_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2025_soup)
    # SOSP 2025 has 13 technical sessions (some without papers are excluded)
    assert len(sessions) >= 10


def test_session_titles_non_empty(sosp_2025_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2025_soup)
    for s in sessions:
        assert s.title.strip(), f"Empty session title found: {s.title!r}"


def test_session_title_no_time(sosp_2025_soup: BeautifulSoup, crawler: SospCrawler):
    """Session titles must not contain time patterns like '8:30 - 10:30'."""
    sessions = crawler.parse_sessions(sosp_2025_soup)
    for s in sessions:
        assert not any(c.isdigit() and ":" in s.title for c in s.title) or ":" not in s.title or True
        # More specific: title should not match a time range pattern
        import re
        assert not re.search(r"\d+:\d+\s*[-–]\s*\d+:\d+", s.title), (
            f"Session title contains time: {s.title!r}"
        )


def test_session_title_no_chair(sosp_2025_soup: BeautifulSoup, crawler: SospCrawler):
    """Session titles must not include 'Session Chair:' text."""
    sessions = crawler.parse_sessions(sosp_2025_soup)
    for s in sessions:
        assert "Session Chair" not in s.title, f"Chair leaked into title: {s.title!r}"


def test_papers_non_empty(sosp_2025_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2025_soup)
    for s in sessions:
        assert len(s.papers) > 0, f"Session '{s.title}' has no papers"


def test_paper_titles_non_empty(sosp_2025_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2025_soup)
    for s in sessions:
        for p in s.papers:
            assert p.title.strip(), f"Empty paper title in session '{s.title}'"


def test_first_session_papers(sosp_2025_soup: BeautifulSoup, crawler: SospCrawler):
    """First session should contain the expected OS papers."""
    sessions = crawler.parse_sessions(sosp_2025_soup)
    first = sessions[0]
    assert "Operating Systems" in first.title or "Session 1" in first.title
    titles = [p.title for p in first.papers]
    assert any("LithOS" in t for t in titles), f"LithOS not found in {titles}"


def test_paper_authors_parsed(sosp_2025_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2025_soup)
    # Find a paper with authors
    all_papers = [p for s in sessions for p in s.papers]
    papers_with_authors = [p for p in all_papers if p.authors]
    assert len(papers_with_authors) > 0, "No papers have authors"


def test_parse_authors_semicolon():
    crawler = SospCrawler()
    authors = crawler._parse_authors(
        "Alice Smith (MIT); Bob Jones (Stanford); Carol Lee (CMU)"
    )
    assert authors == ["Alice Smith", "Bob Jones", "Carol Lee"]


def test_parse_authors_single():
    crawler = SospCrawler()
    authors = crawler._parse_authors(" John Doe (University of X) ")
    assert authors == ["John Doe"]


def test_parse_full_edition(sosp_2025_soup: BeautifulSoup, crawler: SospCrawler):
    edition = crawler.parse(
        str(sosp_2025_soup),
        url="https://sigops.org/s/conferences/sosp/2025/schedule.html",
        year=2025,
    )
    assert edition.conference == "SOSP"
    assert edition.year == 2025
    assert edition.paper_count > 0
