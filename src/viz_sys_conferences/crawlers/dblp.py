"""Crawler for DBLP conference bibliography pages.

DBLP provides consistent, well-structured HTML for all conferences back to
the 1980s. Used for editions that predate the individual conference websites
we can scrape (pre-2012 USENIX, pre-2019 EuroSys, pre-2013 SOSP).

URL pattern: https://dblp.org/db/conf/{venue}/{venue}{year}.html

HTML structure (consistent across all venues and years):
  <h2 [id="sec..."]>Session Title</h2>
  <ul>
    <li>
      <a href="...pid/...">Author Name</a>, ...:
      <strong>Paper Title.</strong>
    </li>
    ...
  </ul>
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from viz_sys_conferences.crawlers.base import BaseCrawler
from viz_sys_conferences.models import Paper, Session

# h2 text patterns that are not real session titles on DBLP pages
_SKIP_H2 = re.compile(
    r"^(editor|volume|contents|proceedings|colocated|co-located|"
    r"invited|keynote|informal|short|demo|poster|workshop|"
    r"external links?|note)s?$",
    re.IGNORECASE,
)


class DblpCrawler(BaseCrawler):
    """Crawler for DBLP conference bibliography pages.

    Handles the consistent DBLP HTML format used across all venues and years:
    h2 section headers followed by ul > li paper entries with author links
    and a strong tag for the paper title.
    """

    conference_name: str

    def __init__(self, conference_name: str) -> None:
        self.conference_name = conference_name

    def parse_sessions(self, soup: BeautifulSoup) -> list[Session]:
        sessions: list[Session] = []
        for h2 in soup.select("h2"):
            title = self._clean_text(h2.get_text())
            if not title or _SKIP_H2.match(title):
                continue
            ul = h2.find_next_sibling("ul")
            if ul is None:
                continue
            papers = self._parse_papers(ul)
            if papers:
                sessions.append(Session(title=title, papers=papers))
        return sessions

    def _parse_papers(self, ul: Tag) -> list[Paper]:
        papers: list[Paper] = []
        for li in ul.find_all("li", recursive=False):
            paper = self._parse_paper(li)
            if paper:
                papers.append(paper)
        return papers

    def _parse_paper(self, li: Tag) -> Paper | None:
        # Title: in a <strong> tag (all venues except some NSDI years)
        strong = li.find("strong")
        if strong:
            title = self._clean_text(strong.get_text()).rstrip(".")
        else:
            # Fallback: plain text after the last author link and colon
            title = self._extract_title_from_text(li)
        if not title or len(title) < 5:
            return None

        # Authors: <a href="...pid/..."> elements
        authors = [
            self._clean_text(a.get_text()) for a in li.find_all("a", href=re.compile(r"/pid/"))
        ]

        return Paper(title=title, authors=authors)

    def _extract_title_from_text(self, li: Tag) -> str:
        """Extract title from plain text after the colon following author names."""
        text = li.get_text(separator=" ")
        # Authors are followed by a colon then the title then page numbers
        # e.g. "Alice, Bob: Some Title. 1-16"
        m = re.search(r":\s+(.+?)\.?\s*\d+[-–]\d+\s*$", text)
        if m:
            return self._clean_text(m.group(1))
        # Last resort: strip page numbers from end
        text = re.sub(r"\s+\d+[-–]\d+\s*$", "", text.strip())
        return self._clean_text(text)
