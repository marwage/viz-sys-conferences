from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from viz_sys_conferences.crawlers.base import BaseCrawler
from viz_sys_conferences.models import Paper, Session

_SKIP_ROW_CLASSES = {"break-row", "event-row", "reg-row", "opening-row", "award-row"}

# h5/h6 labels that are not technical sessions
_NON_SESSION_LABELS = re.compile(
    r"^(registration|coffee|break|lunch|dinner|breakfast|poster|reception|"
    r"opening|closing|general assembly|workshop|welcome|sponsor|award)",
    re.IGNORECASE,
)


class EuroSysCrawler(BaseCrawler):
    """Crawler for EuroSys schedule pages across multiple HTML eras.

    Era detection (priority order):
    - table.prog + td.session-cell  → 2026
    - table.pap + thead.pap         → 2025
    - td[id] + ul.sch               → 2023/2024
    - h5 elements                   → 2022
    - h6 elements                   → 2019
    """

    conference_name = "EuroSys"

    def parse_sessions(self, soup: BeautifulSoup) -> list[Session]:
        if soup.select("td.session-cell"):
            return self._parse_2026(soup)
        if soup.select("table.pap"):
            return self._parse_2025(soup)
        if [td for td in soup.select("td[id]") if td.select_one("ul.sch")]:
            return self._parse_2023_2024(soup)
        if soup.select("h5"):
            return self._parse_2022(soup)
        if soup.select("h6"):
            return self._parse_2019(soup)
        return []

    # ── 2026: table.prog + td.session-cell ────────────────────────────────────

    def _parse_2026(self, soup: BeautifulSoup) -> list[Session]:
        sessions: list[Session] = []
        current_title: str | None = None
        current_papers: list[Paper] = []

        def _flush() -> None:
            if current_title and current_papers:
                sessions.append(Session(title=current_title, papers=list(current_papers)))

        for table in soup.select("table.prog"):
            for row in table.select("tr"):
                if set(row.get("class") or []) & _SKIP_ROW_CLASSES:
                    continue
                tds = row.select("td")
                if not tds:
                    continue
                session_td = row.select_one("td.session-cell")
                if session_td is not None:
                    _flush()
                    current_papers = []
                    current_title = self._session_title_from_cell(session_td)
                    for td in tds:
                        if td is not session_td:
                            paper = self._paper_from_td(td)
                            if paper:
                                current_papers.append(paper)
                elif current_title is not None:
                    for td in tds:
                        paper = self._paper_from_td(td)
                        if paper:
                            current_papers.append(paper)

        _flush()
        return sessions

    def _session_title_from_cell(self, td: Tag) -> str:
        br = td.find("br")
        if br:
            parts = [
                node.get_text() if hasattr(node, "get_text") else str(node)
                for node in br.next_siblings
            ]
            return self._clean_text("".join(parts))
        return self._clean_text(td.get_text())

    def _paper_from_td(self, td: Tag) -> Paper | None:
        br = td.find("br")
        if br is None:
            text = self._clean_text(td.get_text())
            return Paper(title=text) if len(text) > 10 else None
        title_parts = [
            node.get_text() if hasattr(node, "get_text") else str(node)
            for node in td.children
            if node is not br
        ]
        title = self._clean_text("".join(title_parts))
        if not title:
            return None
        small = td.find("small")
        authors = self._parse_authors_comma(small.get_text()) if small else []
        award = "Best Paper" if re.search(r"best\s+paper", td.get_text(), re.IGNORECASE) else None
        return Paper(title=title, authors=authors, award=award)

    # ── 2025: table.pap with thead.pap (3-column) ─────────────────────────────

    def _parse_2025(self, soup: BeautifulSoup) -> list[Session]:
        sessions: list[Session] = []
        for table in soup.select("table.pap"):
            thead = table.select_one("thead")
            if thead is None:
                continue
            th = thead.select_one("th")
            if th is None:
                continue
            # Session title is the first text content of the th, before sub-spans
            session_title = self._clean_text(th.get_text())
            # Strip "Location: ..." and "Chair: ..." suffixes
            session_title = re.sub(
                r"\s*-\s*(Location|Chair):.*$", "", session_title, flags=re.IGNORECASE
            ).strip()
            papers: list[Paper] = []
            for row in table.select("tbody tr"):
                tds = row.select("td")
                if len(tds) < 2:
                    continue
                title = self._clean_text(tds[1].get_text())
                authors = self._parse_authors_comma(tds[2].get_text()) if len(tds) > 2 else []
                if title:
                    papers.append(Paper(title=title, authors=authors))
            if papers:
                sessions.append(Session(title=session_title, papers=papers))
        return sessions

    # ── 2023/2024: td[id] + ul.sch ────────────────────────────────────────────

    def _parse_2023_2024(self, soup: BeautifulSoup) -> list[Session]:
        sessions: list[Session] = []
        for td in soup.select("td[id]"):
            ul = td.select_one("ul.sch")
            if ul is None:
                continue
            strong = td.select_one("strong")
            if strong is None:
                continue
            # "Session A: Graphs<br/>(Session Chair: ...)"
            title_text = strong.get_text(separator=" ")
            title = re.sub(r"\s*\(Session Chair:.*\)", "", title_text, flags=re.IGNORECASE)
            title = self._clean_text(title)
            papers: list[Paper] = []
            for li in ul.select("li"):
                br = li.find("br")
                if br:
                    title_parts = [
                        node.get_text() if hasattr(node, "get_text") else str(node)
                        for node in li.children
                        if node is not br
                    ]
                    paper_title = self._clean_text("".join(title_parts))
                else:
                    paper_title = self._clean_text(li.get_text())
                small = li.find("small")
                authors = self._parse_authors_comma(small.get_text()) if small else []
                if paper_title:
                    papers.append(Paper(title=paper_title, authors=authors))
            if papers:
                sessions.append(Session(title=title, papers=papers))
        return sessions

    # ── 2022: h5 + ul > li ────────────────────────────────────────────────────

    def _parse_2022(self, soup: BeautifulSoup) -> list[Session]:
        sessions: list[Session] = []
        h5_elements = soup.select("h5")
        for h5 in h5_elements:
            raw_title = h5.get_text(strip=True)
            # Strip leading time "09:30 – "
            title = re.sub(r"^\d+:\d+\s*[–-]\s*", "", raw_title).strip()
            if _NON_SESSION_LABELS.match(title):
                continue
            # Collect the first ul sibling (skip intervening p/br elements)
            ul = None
            sib = h5.next_sibling
            while sib:
                if hasattr(sib, "name"):
                    if sib.name == "ul":
                        ul = sib
                        break
                    if sib.name == "h5":
                        break  # next session, stop looking
                sib = sib.next_sibling
            if ul is None:
                continue
            papers: list[Paper] = []
            for li in ul.select("li"):
                a = li.select_one("a")
                i_tag = li.select_one("i")
                if a is None:
                    continue
                paper_title = self._clean_text(a.get_text())
                authors = self._parse_authors_comma(i_tag.get_text()) if i_tag else []
                if paper_title:
                    papers.append(Paper(title=paper_title, authors=authors))
            if papers:
                sessions.append(Session(title=title, papers=papers))
        return sessions

    # ── 2019: h6 + div ────────────────────────────────────────────────────────

    def _parse_2019(self, soup: BeautifulSoup) -> list[Session]:
        sessions: list[Session] = []
        for h6 in soup.select("h6"):
            title = self._clean_text(h6.get_text())
            if _NON_SESSION_LABELS.match(title):
                continue
            # Collect content divs until next h6
            papers: list[Paper] = []
            sib = h6.next_sibling
            while sib:
                if hasattr(sib, "name") and sib.name == "h6":
                    break
                if hasattr(sib, "name") and sib.name == "div":
                    papers.extend(self._extract_papers_2019(sib))
                sib = sib.next_sibling
            if papers:
                sessions.append(Session(title=title, papers=papers))
        return sessions

    def _extract_papers_2019(self, div: Tag) -> list[Paper]:
        """Extract papers from a 2019-era content div.

        Format: <b>TITLE</b><br/>AUTHORS<br/>...<br/><b>TITLE2</b>...
        """
        papers: list[Paper] = []
        current_title: str | None = None
        for child in div.children:
            if hasattr(child, "name"):
                if child.name == "b":
                    if current_title:
                        papers.append(Paper(title=current_title))
                    current_title = self._clean_text(child.get_text())
                elif child.name == "br" and current_title:
                    pass  # separator
            else:
                # NavigableString — might be author text
                text = str(child).strip()
                if text and current_title and papers and papers[-1].title == current_title:
                    # Already appended, update authors
                    pass
                elif text and current_title:
                    # First text after title = authors
                    authors = self._parse_authors_semicolon(text)
                    papers.append(Paper(title=current_title, authors=authors))
                    current_title = None
        if current_title and (not papers or papers[-1].title != current_title):
            papers.append(Paper(title=current_title))
        return papers

    # ── Shared author parsers ─────────────────────────────────────────────────

    def _parse_authors_comma(self, raw: str) -> list[str]:
        """Split author string by comma, handling affiliations in parentheses."""
        parts = [p.strip() for p in raw.split(",")]
        authors: list[str] = []
        buf: list[str] = []
        depth = 0
        for part in parts:
            depth += part.count("(") - part.count(")")
            buf.append(part)
            if depth <= 0:
                full = ",".join(buf).strip()
                name = re.sub(r"\s*\(.*?\)\s*", "", full, flags=re.DOTALL).strip()
                if name:
                    authors.append(name)
                buf = []
                depth = 0
        if buf:
            full = ",".join(buf).strip()
            name = re.sub(r"\s*\(.*?\)\s*", "", full, flags=re.DOTALL).strip()
            if name:
                authors.append(name)
        return authors

    def _parse_authors_semicolon(self, raw: str) -> list[str]:
        """Split author string on semicolons."""
        parts = re.split(r"\s*;\s*", raw.strip())
        return [p.strip() for p in parts if p.strip()]
