from datetime import date

import pytest

from viz_sys_conferences.models import ConferenceEdition, Paper, Session


def test_paper_no_abstract():
    paper = Paper(title="Rethinking the OS Kernel")
    assert paper.abstract is None
    assert paper.authors == []
    assert paper.award is None


def test_paper_with_all_fields():
    paper = Paper(
        title="Fast Storage",
        authors=["Alice", "Bob"],
        abstract="We present a fast storage system.",
        award="Best Paper",
    )
    assert paper.award == "Best Paper"
    assert len(paper.authors) == 2


def test_session_defaults():
    session = Session(title="OS Design")
    assert session.papers == []
    assert session.chair is None


def test_conference_edition_paper_count():
    edition = ConferenceEdition(
        conference="OSDI",
        year=2024,
        url="https://example.com",
        crawled_at=date.today(),
        sessions=[
            Session(title="S1", papers=[Paper(title="P1"), Paper(title="P2")]),
            Session(title="S2", papers=[Paper(title="P3")]),
        ],
    )
    assert edition.paper_count == 3


def test_conference_edition_empty_sessions():
    edition = ConferenceEdition(
        conference="SOSP",
        year=2025,
        url="https://example.com",
        crawled_at=date.today(),
    )
    assert edition.paper_count == 0
    assert edition.sessions == []


def test_conference_edition_json_roundtrip():
    edition = ConferenceEdition(
        conference="EuroSys",
        year=2026,
        url="https://example.com",
        crawled_at=date(2026, 4, 21),
        sessions=[
            Session(
                title="Systems",
                papers=[Paper(title="A Paper", authors=["Author One"])],
            )
        ],
    )
    json_str = edition.model_dump_json()
    restored = ConferenceEdition.model_validate_json(json_str)
    assert restored.conference == "EuroSys"
    assert restored.paper_count == 1
    assert restored.sessions[0].papers[0].authors == ["Author One"]
