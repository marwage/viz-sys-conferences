"""Tests for USENIX parsing across different HTML eras."""
from pathlib import Path

from bs4 import BeautifulSoup

from viz_sys_conferences.crawlers.usenix import UsenixCrawler

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / f"{name}.html").read_text(), "lxml")


def test_nsdi12_session_count():
    crawler = UsenixCrawler("NSDI")
    sessions = crawler.parse_sessions(_load("usenix_nsdi12"))
    assert len(sessions) >= 8


def test_nsdi12_papers_extracted():
    crawler = UsenixCrawler("NSDI")
    sessions = crawler.parse_sessions(_load("usenix_nsdi12"))
    all_papers = [p for s in sessions for p in s.papers]
    assert len(all_papers) >= 20


def test_nsdi12_authors_extracted():
    crawler = UsenixCrawler("NSDI")
    sessions = crawler.parse_sessions(_load("usenix_nsdi12"))
    all_papers = [p for s in sessions for p in s.papers]
    assert any(p.authors for p in all_papers)


def test_nsdi12_known_paper():
    crawler = UsenixCrawler("NSDI")
    sessions = crawler.parse_sessions(_load("usenix_nsdi12"))
    titles = [p.title for s in sessions for p in s.papers]
    assert any("Jellyfish" in t for t in titles), f"Jellyfish not found: {titles[:5]}"


def test_nsdi12_session_titles_not_dates():
    crawler = UsenixCrawler("NSDI")
    sessions = crawler.parse_sessions(_load("usenix_nsdi12"))
    import re
    for s in sessions:
        assert not re.match(r"^(Monday|Tuesday|Wednesday|Thursday|Friday)", s.title), (
            f"Date leaked into session title: {s.title!r}"
        )
