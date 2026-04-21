"""Tests for SOSP parsing across different HTML eras."""
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from viz_sys_conferences.crawlers.sosp import SospCrawler

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def crawler() -> SospCrawler:
    return SospCrawler()


# ── ACM TOC era (2021, 2023) ──────────────────────────────────────────────────

@pytest.fixture
def sosp_2021_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "sosp_2021_toc.html").read_text(), "lxml")


@pytest.fixture
def sosp_2023_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "sosp_2023_toc.html").read_text(), "lxml")


def test_2021_session_count(sosp_2021_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2021_soup)
    assert len(sessions) >= 10


def test_2021_abstracts_present(sosp_2021_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2021_soup)
    all_papers = [p for s in sessions for p in s.papers]
    papers_with_abstracts = [p for p in all_papers if p.abstract]
    assert len(papers_with_abstracts) > 0, "SOSP 2021 toc.html should have abstracts"


def test_2021_authors_present(sosp_2021_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2021_soup)
    all_papers = [p for s in sessions for p in s.papers]
    papers_with_authors = [p for p in all_papers if p.authors]
    assert len(papers_with_authors) > 0


def test_2021_session_titles_strip_prefix(sosp_2021_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2021_soup)
    for s in sessions:
        assert not s.title.upper().startswith("SESSION:"), (
            f"'SESSION:' prefix not stripped from: {s.title!r}"
        )


def test_2023_session_count(sosp_2023_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2023_soup)
    assert len(sessions) >= 8


def test_2023_abstracts_present(sosp_2023_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2023_soup)
    all_papers = [p for s in sessions for p in s.papers]
    assert any(p.abstract for p in all_papers), "SOSP 2023 toc.html should have abstracts"


# ── tr.info era (2013, 2017, 2019) ───────────────────────────────────────────

@pytest.fixture
def sosp_2017_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "sosp_2017.html").read_text(), "lxml")


@pytest.fixture
def sosp_2019_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "sosp_2019.html").read_text(), "lxml")


@pytest.fixture
def sosp_2013_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "sosp_2013.html").read_text(), "lxml")


def test_2017_session_count(sosp_2017_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2017_soup)
    assert len(sessions) >= 8


def test_2017_papers_have_authors(sosp_2017_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2017_soup)
    all_papers = [p for s in sessions for p in s.papers]
    assert any(p.authors for p in all_papers)


def test_2017_known_paper(sosp_2017_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2017_soup)
    titles = [p.title for s in sessions for p in s.papers]
    assert any("DeepXplore" in t for t in titles), f"DeepXplore not found: {titles[:5]}"


def test_2019_session_count(sosp_2019_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2019_soup)
    assert len(sessions) >= 8


def test_2019_papers_non_empty(sosp_2019_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2019_soup)
    for s in sessions:
        assert s.papers, f"Session '{s.title}' has no papers"


def test_2013_session_count(sosp_2013_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2013_soup)
    assert len(sessions) >= 8


def test_2013_known_paper(sosp_2013_soup: BeautifulSoup, crawler: SospCrawler):
    sessions = crawler.parse_sessions(sosp_2013_soup)
    titles = [p.title for s in sessions for p in s.papers]
    assert any("Commutativity" in t for t in titles), f"Commutativity not found: {titles[:5]}"
