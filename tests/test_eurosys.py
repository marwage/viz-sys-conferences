from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from viz_sys_conferences.crawlers.eurosys import EuroSysCrawler

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def eurosys_2026_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "eurosys_2026.html").read_text(), "lxml")


@pytest.fixture
def crawler() -> EuroSysCrawler:
    return EuroSysCrawler()


def test_session_count(eurosys_2026_soup: BeautifulSoup, crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(eurosys_2026_soup)
    # EuroSys 2026 preliminary program has 6 technical sessions (3 days × 2 slots)
    assert len(sessions) >= 6


def test_session_titles_non_empty(eurosys_2026_soup: BeautifulSoup, crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(eurosys_2026_soup)
    for s in sessions:
        assert s.title.strip(), f"Empty session title: {s.title!r}"


def test_session_title_no_time(eurosys_2026_soup: BeautifulSoup, crawler: EuroSysCrawler):
    """Session titles must not contain time ranges."""
    import re
    sessions = crawler.parse_sessions(eurosys_2026_soup)
    for s in sessions:
        assert not re.search(r"\d+:\d+\s*[–-]\s*\d+:\d+", s.title), (
            f"Session title contains time: {s.title!r}"
        )


def test_papers_per_session(eurosys_2026_soup: BeautifulSoup, crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(eurosys_2026_soup)
    for s in sessions:
        assert len(s.papers) >= 1, f"Session '{s.title}' has no papers"


def test_paper_titles_non_empty(eurosys_2026_soup: BeautifulSoup, crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(eurosys_2026_soup)
    for s in sessions:
        for p in s.papers:
            assert p.title.strip(), f"Empty paper title in session '{s.title}'"


def test_paper_authors_extracted(eurosys_2026_soup: BeautifulSoup, crawler: EuroSysCrawler):
    sessions = crawler.parse_sessions(eurosys_2026_soup)
    all_papers = [p for s in sessions for p in s.papers]
    papers_with_authors = [p for p in all_papers if p.authors]
    assert len(papers_with_authors) > 0, "No papers have authors"


def test_known_session_present(eurosys_2026_soup: BeautifulSoup, crawler: EuroSysCrawler):
    """The OS & Virtualization session should be present."""
    sessions = crawler.parse_sessions(eurosys_2026_soup)
    titles = [s.title for s in sessions]
    assert any("Virtualization" in t or "OS" in t for t in titles), (
        f"OS/Virtualization session not found. Titles: {titles}"
    )


def test_known_paper_present(eurosys_2026_soup: BeautifulSoup, crawler: EuroSysCrawler):
    """RaidenSwap should appear in the OS & Virtualization session."""
    sessions = crawler.parse_sessions(eurosys_2026_soup)
    all_paper_titles = [p.title for s in sessions for p in s.papers]
    assert any("RaidenSwap" in t for t in all_paper_titles), (
        f"RaidenSwap not found. Paper titles: {all_paper_titles[:5]}"
    )


def test_parse_authors_comma_separated():
    crawler = EuroSysCrawler()
    authors = crawler._parse_authors_comma(
        "Alice Smith (MIT), Bob Jones (Stanford), Carol Lee (CMU)"
    )
    assert "Alice Smith" in authors
    assert "Bob Jones" in authors
    assert "Carol Lee" in authors


def test_parse_authors_nested_parentheses():
    crawler = EuroSysCrawler()
    authors = crawler._parse_authors_comma(
        "Minkyu Jung (KAIST), Chanshin Kwak (School of Computing, KAIST)"
    )
    assert "Minkyu Jung" in authors
    assert "Chanshin Kwak" in authors


def test_parse_full_edition(eurosys_2026_soup: BeautifulSoup, crawler: EuroSysCrawler):
    edition = crawler.parse(
        str(eurosys_2026_soup),
        url="https://2026.eurosys.org/preliminary-program.html",
        year=2026,
    )
    assert edition.conference == "EuroSys"
    assert edition.year == 2026
    assert edition.paper_count > 0
