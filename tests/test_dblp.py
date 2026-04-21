"""Tests for the DBLP crawler using synthetic fixtures."""

from pathlib import Path

from bs4 import BeautifulSoup

from viz_sys_conferences.crawlers.dblp import DblpCrawler

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / name).read_text(), "lxml")


def test_eurosys2008_session_count():
    crawler = DblpCrawler("EuroSys")
    sessions = crawler.parse_sessions(_load("dblp_eurosys2008.html"))
    assert len(sessions) == 3


def test_eurosys2008_session_titles():
    crawler = DblpCrawler("EuroSys")
    sessions = crawler.parse_sessions(_load("dblp_eurosys2008.html"))
    titles = [s.title for s in sessions]
    assert "Scheduling" in titles
    assert "Distributed Storage" in titles
    assert "File Systems" in titles


def test_eurosys2008_paper_count():
    crawler = DblpCrawler("EuroSys")
    sessions = crawler.parse_sessions(_load("dblp_eurosys2008.html"))
    total = sum(len(s.papers) for s in sessions)
    assert total == 5


def test_eurosys2008_paper_title():
    crawler = DblpCrawler("EuroSys")
    sessions = crawler.parse_sessions(_load("dblp_eurosys2008.html"))
    titles = [p.title for s in sessions for p in s.papers]
    assert any("Task activity vectors" in t for t in titles)


def test_eurosys2008_trailing_period_stripped():
    """DBLP titles end with a period which should be stripped."""
    crawler = DblpCrawler("EuroSys")
    sessions = crawler.parse_sessions(_load("dblp_eurosys2008.html"))
    for s in sessions:
        for p in s.papers:
            assert not p.title.endswith("."), f"Trailing period in: {p.title!r}"


def test_eurosys2008_authors():
    crawler = DblpCrawler("EuroSys")
    sessions = crawler.parse_sessions(_load("dblp_eurosys2008.html"))
    all_authors = [a for s in sessions for p in s.papers for a in p.authors]
    assert "Andreas Merkel" in all_authors
    assert "Frank Bellosa" in all_authors


def test_sosp2011_session_count():
    crawler = DblpCrawler("SOSP")
    sessions = crawler.parse_sessions(_load("dblp_sosp2011.html"))
    assert len(sessions) == 3


def test_sosp2011_known_paper():
    crawler = DblpCrawler("SOSP")
    sessions = crawler.parse_sessions(_load("dblp_sosp2011.html"))
    titles = [p.title for s in sessions for p in s.papers]
    assert any("SILT" in t for t in titles)


def test_sosp2011_multi_author():
    crawler = DblpCrawler("SOSP")
    sessions = crawler.parse_sessions(_load("dblp_sosp2011.html"))
    silt_paper = next(p for s in sessions for p in s.papers if "SILT" in p.title)
    assert len(silt_paper.authors) == 4


def test_parse_full_edition():
    crawler = DblpCrawler("EuroSys")
    edition = crawler.parse(
        (FIXTURES / "dblp_eurosys2008.html").read_text(),
        url="https://dblp.org/db/conf/eurosys/eurosys2008.html",
        year=2008,
    )
    assert edition.conference == "EuroSys"
    assert edition.year == 2008
    assert edition.paper_count == 5
