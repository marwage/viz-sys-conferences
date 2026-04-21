from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from viz_sys_conferences.crawlers.usenix import UsenixCrawler

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def osdi25_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "usenix_osdi25.html").read_text(), "lxml")


@pytest.fixture
def crawler() -> UsenixCrawler:
    return UsenixCrawler(conference_name="OSDI")


def test_session_count(osdi25_soup: BeautifulSoup, crawler: UsenixCrawler):
    sessions = crawler.parse_sessions(osdi25_soup)
    # OSDI 2025 has ~13 node-session articles (some are non-paper sessions)
    assert len(sessions) >= 5


def test_session_titles_non_empty(osdi25_soup: BeautifulSoup, crawler: UsenixCrawler):
    sessions = crawler.parse_sessions(osdi25_soup)
    for s in sessions:
        assert s.title.strip(), f"Empty session title: {s.title!r}"


def test_papers_per_session(osdi25_soup: BeautifulSoup, crawler: UsenixCrawler):
    sessions = crawler.parse_sessions(osdi25_soup)
    for s in sessions:
        assert len(s.papers) >= 1, f"Session '{s.title}' has no papers"


def test_paper_titles_non_empty(osdi25_soup: BeautifulSoup, crawler: UsenixCrawler):
    sessions = crawler.parse_sessions(osdi25_soup)
    for s in sessions:
        for p in s.papers:
            assert p.title.strip(), f"Empty paper title in session '{s.title}'"


def test_paper_authors_extracted(osdi25_soup: BeautifulSoup, crawler: UsenixCrawler):
    sessions = crawler.parse_sessions(osdi25_soup)
    all_papers = [p for s in sessions for p in s.papers]
    papers_with_authors = [p for p in all_papers if p.authors]
    assert len(papers_with_authors) > 0, "No papers have authors"


def test_known_session_present(osdi25_soup: BeautifulSoup, crawler: UsenixCrawler):
    """Distributed Systems and Data Centers I should be present."""
    sessions = crawler.parse_sessions(osdi25_soup)
    titles = [s.title for s in sessions]
    assert any("Distributed Systems" in t for t in titles), (
        f"Distributed Systems session not found. Titles: {titles}"
    )


def test_known_paper_present(osdi25_soup: BeautifulSoup, crawler: UsenixCrawler):
    """Basilisk paper should appear in the Distributed Systems session."""
    sessions = crawler.parse_sessions(osdi25_soup)
    all_titles = [p.title for s in sessions for p in s.papers]
    assert any("Basilisk" in t for t in all_titles), (
        f"Basilisk not found. Titles: {all_titles[:5]}"
    )


def test_abstracts_extracted(osdi25_soup: BeautifulSoup, crawler: UsenixCrawler):
    """At least some papers should have abstracts on USENIX pages."""
    sessions = crawler.parse_sessions(osdi25_soup)
    all_papers = [p for s in sessions for p in s.papers]
    papers_with_abstracts = [p for p in all_papers if p.abstract]
    assert len(papers_with_abstracts) > 0, "No abstracts extracted"


def test_parse_full_edition(osdi25_soup: BeautifulSoup, crawler: UsenixCrawler):
    edition = crawler.parse(
        str(osdi25_soup),
        url="https://www.usenix.org/conference/osdi25/technical-sessions",
        year=2025,
    )
    assert edition.conference == "OSDI"
    assert edition.year == 2025
    assert edition.paper_count > 0
