from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import date

from bs4 import BeautifulSoup

from viz_sys_conferences.models import ConferenceEdition, Session


class BaseCrawler(ABC):
    """Abstract base class for conference schedule crawlers."""

    conference_name: str

    def parse(self, html: str, url: str, year: int) -> ConferenceEdition:
        """Parse raw HTML into a ConferenceEdition.

        Args:
            html: Raw HTML content of the schedule page.
            url: Source URL of the page.
            year: Conference year.

        Returns:
            ConferenceEdition with all parsed sessions and papers.
        """
        soup = BeautifulSoup(html, "lxml")
        sessions = self.parse_sessions(soup)
        return ConferenceEdition(
            conference=self.conference_name,
            year=year,
            url=url,
            crawled_at=date.today(),
            sessions=sessions,
        )

    @abstractmethod
    def parse_sessions(self, soup: BeautifulSoup) -> list[Session]:
        """Extract sessions from the parsed HTML.

        Args:
            soup: BeautifulSoup object of the full page.

        Returns:
            List of Session objects.
        """
        ...

    def _clean_text(self, text: str) -> str:
        """Normalise whitespace in a string."""
        return re.sub(r"\s+", " ", text).strip()
