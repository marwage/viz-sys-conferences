"""Tests for the DBLP dump extractor using an in-memory synthetic XML fixture."""

from __future__ import annotations

import gzip
import tempfile
from pathlib import Path

from viz_sys_conferences.dblp_dump import _clean, _venue, extract_editions

# Minimal DBLP XML with entries for 3 of our target conferences
_SAMPLE_XML = b"""\
<?xml version="1.0" encoding="US-ASCII"?>
<!DOCTYPE dblp SYSTEM "dblp.dtd">
<dblp>

<inproceedings key="conf/osdi/BoydWickizer10" mdate="2024-01-01">
  <author>Silas Boyd-Wickizer</author>
  <author>Austin T. Clements</author>
  <title>An Analysis of Linux Scalability to Many Cores.</title>
  <year>2010</year>
  <booktitle>OSDI</booktitle>
  <crossref>conf/osdi/2010</crossref>
</inproceedings>

<inproceedings key="conf/osdi/Nightingale10" mdate="2024-01-01">
  <author>Edmund B. Nightingale</author>
  <title>Flat Datacenter Storage.</title>
  <year>2010</year>
  <booktitle>OSDI</booktitle>
  <crossref>conf/osdi/2010</crossref>
</inproceedings>

<inproceedings key="conf/nsdi/Adya10" mdate="2024-01-01">
  <author>Atul Adya</author>
  <author>John Dunagan</author>
  <title>Centrifuge: Integrated Lease Management and Partitioning for Cloud Services.</title>
  <year>2010</year>
  <booktitle>NSDI</booktitle>
  <crossref>conf/nsdi/2010</crossref>
</inproceedings>

<inproceedings key="conf/sosp/Lim11" mdate="2024-01-01">
  <author>Hyeontaek Lim</author>
  <author>Bin Fan</author>
  <title>SILT: A Memory-Efficient, High-Performance Key-Value Store.</title>
  <year>2011</year>
  <booktitle>SOSP</booktitle>
  <crossref>conf/sosp/2011</crossref>
</inproceedings>

<inproceedings key="conf/eurosys/SomeAuthor08" mdate="2024-01-01">
  <author>John Smith</author>
  <title>Task Scheduling in Distributed Systems.</title>
  <year>2008</year>
  <booktitle>EuroSys</booktitle>
  <crossref>conf/eurosys/2008</crossref>
</inproceedings>

<inproceedings key="conf/usenix/Example09" mdate="2024-01-01">
  <author>Jane Doe</author>
  <title>Design Tradeoffs for SSD Performance.</title>
  <year>2009</year>
  <booktitle>USENIX Annual Technical Conference</booktitle>
  <crossref>conf/usenix/2009</crossref>
</inproceedings>

<inproceedings key="conf/osdi/Future27" mdate="2024-01-01">
  <author>Future Author</author>
  <title>A Paper From the Future.</title>
  <year>2027</year>
  <booktitle>OSDI</booktitle>
  <crossref>conf/osdi/2027</crossref>
</inproceedings>

<article key="journals/tocs/Example10" mdate="2024-01-01">
  <author>Journal Author</author>
  <title>A Journal Article That Should Be Ignored.</title>
  <year>2010</year>
</article>

</dblp>
"""


def _write_dump(tmp_dir: Path, compress: bool = True) -> Path:
    path = tmp_dir / ("dblp.xml.gz" if compress else "dblp.xml")
    if compress:
        with gzip.open(path, "wb") as f:
            f.write(_SAMPLE_XML)
    else:
        path.write_bytes(_SAMPLE_XML)
    return path


# ── _venue helper ─────────────────────────────────────────────────────────────


def test_venue_osdi():
    assert _venue("conf/osdi/Boyd-WickizerCMPKMZ10") == "OSDI"


def test_venue_nsdi():
    assert _venue("conf/nsdi/Adya10") == "NSDI"


def test_venue_sosp():
    assert _venue("conf/sosp/Lim11") == "SOSP"


def test_venue_eurosys():
    assert _venue("conf/eurosys/Smith08") == "EuroSys"


def test_venue_atc():
    assert _venue("conf/usenix/Doe09") == "ATC"


def test_venue_unrelated():
    assert _venue("conf/sigmod/Example10") is None
    assert _venue("journals/tocs/Example10") is None


# ── _clean helper ─────────────────────────────────────────────────────────────


def test_clean_strips_trailing_period():
    assert _clean("Some Title.") == "Some Title"


def test_clean_normalises_whitespace():
    assert _clean("  Foo   Bar  ") == "Foo Bar"


def test_clean_none():
    assert _clean(None) == ""


# ── extract_editions ──────────────────────────────────────────────────────────


def test_extract_editions_count():
    with tempfile.TemporaryDirectory() as tmp:
        dump = _write_dump(Path(tmp))
        editions = extract_editions(dump, start_year=2006, end_year=2026)
    # 5 unique (conference, year) pairs within range
    assert len(editions) == 5


def test_extract_editions_sorted():
    with tempfile.TemporaryDirectory() as tmp:
        dump = _write_dump(Path(tmp))
        editions = extract_editions(dump, start_year=2006, end_year=2026)
    pairs = [(e.conference, e.year) for e in editions]
    assert pairs == sorted(pairs)


def test_extract_editions_year_filter():
    """Papers outside start/end_year should not appear."""
    with tempfile.TemporaryDirectory() as tmp:
        dump = _write_dump(Path(tmp))
        editions = extract_editions(dump, start_year=2006, end_year=2026)
    years = [e.year for e in editions]
    assert 2027 not in years


def test_extract_editions_journal_excluded():
    """<article> entries (journals) must be excluded."""
    with tempfile.TemporaryDirectory() as tmp:
        dump = _write_dump(Path(tmp))
        editions = extract_editions(dump, start_year=2006, end_year=2026)
    all_titles = [p.title for e in editions for p in e.papers]
    assert not any("Journal Article" in t for t in all_titles)


def test_extract_osdi_2010_papers():
    with tempfile.TemporaryDirectory() as tmp:
        dump = _write_dump(Path(tmp))
        editions = extract_editions(dump, start_year=2006, end_year=2026)
    osdi = next(e for e in editions if e.conference == "OSDI" and e.year == 2010)
    assert osdi.paper_count == 2
    titles = [p.title for p in osdi.papers]
    assert any("Scalability" in t for t in titles)
    assert any("Flat Datacenter" in t for t in titles)


def test_extract_trailing_period_stripped():
    with tempfile.TemporaryDirectory() as tmp:
        dump = _write_dump(Path(tmp))
        editions = extract_editions(dump, start_year=2006, end_year=2026)
    for e in editions:
        for p in e.papers:
            assert not p.title.endswith("."), f"Trailing period: {p.title!r}"


def test_extract_authors():
    with tempfile.TemporaryDirectory() as tmp:
        dump = _write_dump(Path(tmp))
        editions = extract_editions(dump, start_year=2006, end_year=2026)
    osdi = next(e for e in editions if e.conference == "OSDI" and e.year == 2010)
    scalability = next(p for p in osdi.papers if "Scalability" in p.title)
    assert "Silas Boyd-Wickizer" in scalability.authors
    assert "Austin T. Clements" in scalability.authors


def test_extract_all_five_conferences():
    with tempfile.TemporaryDirectory() as tmp:
        dump = _write_dump(Path(tmp))
        editions = extract_editions(dump, start_year=2006, end_year=2026)
    conferences = {e.conference for e in editions}
    assert conferences == {"OSDI", "NSDI", "SOSP", "EuroSys", "ATC"}


def test_extract_uncompressed_dump():
    """Should also work with uncompressed .xml files."""
    with tempfile.TemporaryDirectory() as tmp:
        dump = _write_dump(Path(tmp), compress=False)
        editions = extract_editions(dump, start_year=2006, end_year=2026)
    assert len(editions) == 5
