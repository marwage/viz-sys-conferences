from __future__ import annotations

import re

from bs4 import BeautifulSoup, NavigableString, Tag

from viz_sys_conferences.models import Paper, Session
from viz_sys_conferences.crawlers.base import BaseCrawler

# Patterns for SOSP session title rows in tr.info (strip time + chair)
_SESSION_PREFIX_RE = re.compile(r"^(Session\s+\d+[A-Z]?:.*?)[\s,]*(?:Chair:|Mon|Tue|Wed|Thu|Fri|\d+:\d+)", re.IGNORECASE)


class SospCrawler(BaseCrawler):
    """Crawler for SOSP schedule pages.

    Supports three HTML eras:
    - 2025: table.table + h4.sch (one table per session)
    - 2013/2017/2019: tr.info sessions + alternating title/author tr rows
    - 2021/2023: ACM DL TOC format (h2 SESSION:, h3 titles, ul.DLauthors, div.DLabstract)
    """

    conference_name = "SOSP"

    def parse_sessions(self, soup: BeautifulSoup) -> list[Session]:
        if soup.select_one("div.DLabstract") or soup.select_one("ul.DLauthors"):
            return self._parse_acm_toc(soup)
        if soup.select_one("h4.sch"):
            return self._parse_schedule_2025(soup)
        if soup.select("tr.info"):
            return self._parse_tr_info(soup)
        return []

    # ── 2025 era ─────────────────────────────────────────────────────────────

    def _parse_schedule_2025(self, soup: BeautifulSoup) -> list[Session]:
        sessions: list[Session] = []
        for table in soup.select("table.table"):
            h4 = table.select_one("h4.sch")
            if h4 is None:
                continue
            session_title = self._extract_session_title_2025(h4)
            chair = self._extract_chair_2025(h4)
            papers = self._extract_papers_2025(table)
            if papers:
                sessions.append(Session(title=session_title, chair=chair, papers=papers))
        return sessions

    def _extract_session_title_2025(self, h4: Tag) -> str:
        for span in h4.select("span"):
            span.decompose()
        return self._clean_text(h4.get_text())

    def _extract_chair_2025(self, h4: Tag) -> str | None:
        chair_span = h4.find("span", class_="sch-sessionchair")
        if chair_span is None:
            return None
        text = self._clean_text(chair_span.get_text())
        return re.sub(r"^Session\s+Chair:\s*", "", text, flags=re.IGNORECASE) or None

    def _extract_papers_2025(self, table: Tag) -> list[Paper]:
        papers: list[Paper] = []
        for row in table.select("tr"):
            strong = row.select_one("strong")
            if strong is None:
                continue
            title = self._clean_text(strong.get_text())
            if not title:
                continue
            em = row.select_one("em, i")
            authors = self._parse_authors(em.get_text()) if em else []
            award = "Best Paper" if "best paper" in row.get_text().lower() else None
            papers.append(Paper(title=title, authors=authors, award=award))
        return papers

    # ── 2013/2017/2019 era (tr.info) ─────────────────────────────────────────

    def _parse_tr_info(self, soup: BeautifulSoup) -> list[Session]:
        """Parse SOSP pages with tr.info session rows and alternating title/author rows.

        The schedule may span multiple tables (one per day), so all tables
        with tr.info rows are processed.
        """
        sessions: list[Session] = []
        current_session: Session | None = None
        pending_title: str | None = None

        all_rows = []
        for table in soup.select("table"):
            if table.select("tr.info"):
                all_rows.extend(table.select("tr"))

        for row in all_rows:
            cls = row.get("class") or []

            if "info" in cls:
                # Session header
                if current_session and current_session.papers:
                    sessions.append(current_session)
                title = self._extract_session_title_tr_info(row)
                chair = self._extract_chair_tr_info(row)
                current_session = Session(title=title, chair=chair, papers=[])
                pending_title = None
                continue

            if "success" in cls:
                # Break row — flush pending title if any
                pending_title = None
                continue

            if current_session is None:
                continue

            row_text = self._clean_text(row.get_text())
            if not row_text:
                continue

            strong = row.select_one("strong")
            if strong:
                # This is a paper title row
                pending_title = self._clean_text(strong.get_text())
            elif pending_title:
                # This is an author row following a title row
                award = None
                if "best paper" in pending_title.lower():
                    pending_title = re.sub(r"^Best\s+Paper\s*", "", pending_title, flags=re.IGNORECASE).strip()
                    award = "Best Paper"
                authors = self._parse_authors(row_text)
                current_session.papers.append(
                    Paper(title=pending_title, authors=authors, award=award)
                )
                pending_title = None

        if current_session and current_session.papers:
            sessions.append(current_session)
        return sessions

    def _extract_session_title_tr_info(self, row: Tag) -> str:
        strong = row.select_one("strong")
        if strong:
            return self._clean_text(strong.get_text())
        text = self._clean_text(row.get_text())
        # Strip trailing time, chair, and location info
        # e.g. "Session 1: Bug hunting, Chair: Shan Lu(China Hall)9:00 AM - 10:15 AM"
        m = re.match(r"^(Session\s+\d+[A-Z]?:.*?)(?:,?\s*(?:Chair:|[A-Z][a-z]+day,|\d+:\d+))", text)
        if m:
            return m.group(1).strip()
        return text.split("(")[0].split(",")[0].strip()

    def _extract_chair_tr_info(self, row: Tag) -> str | None:
        text = self._clean_text(row.get_text())
        m = re.search(r"Chair:\s*([^,()\d]+)", text)
        if m:
            return m.group(1).strip()
        return None

    # ── 2021/2023 ACM TOC era ─────────────────────────────────────────────────

    def _parse_acm_toc(self, soup: BeautifulSoup) -> list[Session]:
        sessions: list[Session] = []
        current_session: Session | None = None

        for el in soup.find_all(["h2", "h3", "ul", "div"]):
            if el.name == "h2":
                if current_session and current_session.papers:
                    sessions.append(current_session)
                raw = el.get_text(strip=True)
                title = re.sub(r"^SESSION:\s*", "", raw, flags=re.IGNORECASE)
                current_session = Session(title=title, papers=[])

            elif el.name == "h3" and current_session is not None:
                title = self._clean_text(el.get_text())
                current_session.papers.append(Paper(title=title))

            elif el.name == "ul" and "DLauthors" in (el.get("class") or []):
                if current_session and current_session.papers:
                    authors = [self._clean_text(li.get_text()) for li in el.select("li") if li.get_text(strip=True)]
                    current_session.papers[-1] = current_session.papers[-1].model_copy(update={"authors": authors})

            elif el.name == "div" and "DLabstract" in (el.get("class") or []):
                if current_session and current_session.papers:
                    abstract = self._clean_text(el.get_text())
                    current_session.papers[-1] = current_session.papers[-1].model_copy(update={"abstract": abstract})

        if current_session and current_session.papers:
            sessions.append(current_session)
        return sessions

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _parse_authors(self, raw: str) -> list[str]:
        """Split a raw author string on semicolons or commas, skipping affiliations."""
        stripped = raw.strip()
        if ";" in stripped:
            parts = re.split(r"\s*;\s*", stripped)
        else:
            parts = self._split_respecting_parens(stripped)

        authors: list[str] = []
        for part in parts:
            name = re.sub(r"\s*\(.*?\)\s*", "", self._clean_text(part)).strip()
            if name:
                authors.append(name)
        return authors

    def _split_respecting_parens(self, text: str) -> list[str]:
        """Split on ', ' while ignoring commas inside parentheses."""
        parts: list[str] = []
        depth = 0
        buf: list[str] = []
        for ch in text:
            if ch == "(":
                depth += 1
                buf.append(ch)
            elif ch == ")":
                depth -= 1
                buf.append(ch)
            elif ch == "," and depth == 0:
                part = "".join(buf).strip()
                if part:
                    parts.append(part)
                buf = []
            else:
                buf.append(ch)
        if buf:
            part = "".join(buf).strip()
            if part:
                parts.append(part)
        return parts
