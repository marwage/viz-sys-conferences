from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from viz_sys_conferences.models import Paper, Session
from viz_sys_conferences.crawlers.base import BaseCrawler

# Matches date headers like "Wednesday, April 25, 2012"
_DATE_HEADER_RE = re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),", re.IGNORECASE)
# Matches "Session Chair:" at the start of a content div — identifies session h2s
_CHAIR_PREFIX_RE = re.compile(r"^Session\s+Chair:", re.IGNORECASE)

_NON_SESSION_H2 = re.compile(
    r"^(break|lunch|dinner|breakfast|poster|reception|keynote|award|sponsor|"
    r"registration|welcome|opening|closing|panel|tutorial|workshop|invited)",
    re.IGNORECASE,
)


class UsenixCrawler(BaseCrawler):
    """Crawler for USENIX conference schedule pages (OSDI, NSDI, ATC).

    Supports two HTML eras:
    - 2016+: Drupal article.node-session / article.node-paper nested structure
    - 2012–2015: flat sequential h2 elements for both sessions and papers
    """

    conference_name: str

    def __init__(self, conference_name: str) -> None:
        self.conference_name = conference_name

    def parse_sessions(self, soup: BeautifulSoup) -> list[Session]:
        if soup.select("article.node-session"):
            return self._parse_article_era(soup)
        if soup.select("div.node-session"):
            return self._parse_div_era(soup)
        return self._parse_flat_h2_era(soup)

    # ── 2016+ era: nested articles ────────────────────────────────────────────

    def _parse_article_era(self, soup: BeautifulSoup) -> list[Session]:
        sessions: list[Session] = []
        for session_article in soup.select("article.node-session"):
            title = self._session_title_from_article(session_article)
            if not title:
                continue
            papers = self._papers_from_article(session_article)
            if papers:
                sessions.append(Session(title=title, papers=papers))
        return sessions

    def _session_title_from_article(self, article: Tag) -> str:
        for child in article.children:
            if getattr(child, "name", None) == "h2":
                text = self._clean_text(child.get_text())
                if text:
                    return text
        return ""

    def _papers_from_article(self, session_article: Tag) -> list[Paper]:
        papers: list[Paper] = []
        for paper_article in session_article.select("article.node-paper"):
            h2 = paper_article.find("h2")
            title = self._clean_text(h2.get_text()) if h2 else ""
            if not title:
                continue
            authors = self._authors_from_paper_article(paper_article)
            abstract = self._abstract_from_paper_article(paper_article)
            papers.append(Paper(title=title, authors=authors, abstract=abstract))
        return papers

    def _authors_from_paper_article(self, article: Tag) -> list[str]:
        div = article.select_one("div.field-name-field-paper-people-text")
        if div is None:
            return []
        raw = div.get_text()
        parts = [p.strip() for p in raw.split(";")]
        return [p.split(",")[0].strip() for p in parts if p.split(",")[0].strip()]

    def _abstract_from_paper_article(self, article: Tag) -> str | None:
        div = article.select_one("div.field-name-field-paper-description-long")
        if div is None:
            return None
        text = self._clean_text(div.get_text())
        return text or None

    # ── 2014–2015 era: div.node-session / div.node-paper ─────────────────────

    def _parse_div_era(self, soup: BeautifulSoup) -> list[Session]:
        """Parse pages using div.node-session with div.node-paper children."""
        sessions: list[Session] = []
        for session_div in soup.select("div.node-session"):
            h2 = session_div.find("h2")
            title = self._clean_text(h2.get_text()) if h2 else ""
            if not title:
                continue
            papers: list[Paper] = []
            for paper_div in session_div.select("div.node-paper"):
                ph2 = paper_div.find("h2")
                ptitle = self._clean_text(ph2.get_text()) if ph2 else ""
                if not ptitle:
                    continue
                authors = self._authors_from_paper_article(paper_div)
                abstract = self._abstract_from_paper_article(paper_div)
                papers.append(Paper(title=ptitle, authors=authors, abstract=abstract))
            if papers:
                sessions.append(Session(title=title, papers=papers))
        return sessions

    # ── 2012–2013 era: flat h2 sequence ───────────────────────────────────────

    def _parse_flat_h2_era(self, soup: BeautifulSoup) -> list[Session]:
        """Parse pages where sessions and papers are sequential h2 elements.

        Strategy:
        - h2 whose following div.content starts with "Session Chair:" → session header
        - h2 whose following div.content has authors → paper title
        - Skip date headers and break/lunch labels
        """
        sessions: list[Session] = []
        current_session: Session | None = None

        h2_elements = soup.select("h2")
        for h2 in h2_elements:
            text = self._clean_text(h2.get_text())
            if not text or _DATE_HEADER_RE.match(text):
                continue

            content_div = self._next_content_div(h2)
            content_text = self._clean_text(content_div.get_text()) if content_div else ""

            if _CHAIR_PREFIX_RE.search(content_text):
                # Session header
                if current_session and current_session.papers:
                    sessions.append(current_session)
                current_session = Session(
                    title=text,
                    chair=self._extract_chair_from_content(content_text),
                    papers=[],
                )
            elif current_session is not None and content_text and not _NON_SESSION_H2.match(text):
                # Paper: title is the h2 text, authors are in content_div
                authors = self._parse_authors_flat(content_text)
                current_session.papers.append(Paper(title=text, authors=authors))

        if current_session and current_session.papers:
            sessions.append(current_session)
        return sessions

    def _next_content_div(self, h2: Tag) -> Tag | None:
        """Find the first div.content sibling immediately after an h2."""
        sib = h2.next_sibling
        while sib:
            if hasattr(sib, "name"):
                if sib.name == "div" and "content" in (sib.get("class") or []):
                    return sib
                if sib.name == "h2":
                    break
            sib = sib.next_sibling
        return None

    def _extract_chair_from_content(self, text: str) -> str | None:
        m = re.search(r"Session\s+Chair:\s*([^,;\n]+)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None

    def _parse_authors_flat(self, text: str) -> list[str]:
        """Parse the first line of a content div as an author list.

        USENIX flat-era format: "Name1, Affiliation1;Name2, Affiliation2"
        or "Name1 and Name2, Affiliation" or "Name1,Name2,Name3,Affiliation"
        """
        # Take content up to any linebreak (after which abstract may follow)
        first_line = re.split(r"\n|(?:\s{3,})", text)[0].strip()
        # Split on semicolons (author separators) first
        if ";" in first_line:
            parts = first_line.split(";")
        else:
            # Comma-separated: group by "Name, Affil" pairs
            parts = [first_line]
        authors: list[str] = []
        for part in parts:
            name = part.split(",")[0].strip()
            # Strip "and" conjunctions
            name = re.sub(r"\s+and\s+", ", ", name)
            if name and len(name) > 1:
                # Could be multiple names joined with " and "
                for n in re.split(r",\s*", name):
                    n = n.strip()
                    if n:
                        authors.append(n)
        return authors
