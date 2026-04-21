from datetime import date

from viz_sys_conferences.models import ConferenceEdition, Paper


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


def test_conference_edition_paper_count():
    edition = ConferenceEdition(
        conference="OSDI",
        year=2024,
        url="https://example.com",
        crawled_at=date.today(),
        papers=[Paper(title="P1"), Paper(title="P2"), Paper(title="P3")],
    )
    assert edition.paper_count == 3


def test_conference_edition_empty():
    edition = ConferenceEdition(
        conference="SOSP",
        year=2025,
        url="https://example.com",
        crawled_at=date.today(),
    )
    assert edition.paper_count == 0
    assert edition.papers == []


def test_conference_edition_json_roundtrip():
    edition = ConferenceEdition(
        conference="EuroSys",
        year=2026,
        url="https://example.com",
        crawled_at=date(2026, 4, 21),
        papers=[Paper(title="A Paper", authors=["Author One"])],
    )
    restored = ConferenceEdition.model_validate_json(edition.model_dump_json())
    assert restored.conference == "EuroSys"
    assert restored.paper_count == 1
    assert restored.papers[0].authors == ["Author One"]
