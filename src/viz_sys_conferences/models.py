from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Paper(BaseModel):
    """A single paper within a conference edition."""

    title: str
    authors: list[str] = []
    abstract: str | None = None
    award: str | None = None


class ConferenceEdition(BaseModel):
    """One year of a conference with all its papers."""

    conference: str
    year: int
    url: str
    crawled_at: date
    papers: list[Paper] = []

    @property
    def paper_count(self) -> int:
        """Total number of papers in this edition."""
        return len(self.papers)
