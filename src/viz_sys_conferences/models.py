from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Paper(BaseModel):
    """A single paper within a conference session."""

    title: str
    authors: list[str] = []
    abstract: str | None = None
    award: str | None = None


class Session(BaseModel):
    """A named session grouping one or more papers."""

    title: str
    chair: str | None = None
    papers: list[Paper] = []


class ConferenceEdition(BaseModel):
    """One year of a conference, with all its sessions and papers."""

    conference: str
    year: int
    url: str
    crawled_at: date
    sessions: list[Session] = []

    @property
    def paper_count(self) -> int:
        """Total number of papers across all sessions."""
        return sum(len(s.papers) for s in self.sessions)
