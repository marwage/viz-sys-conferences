"""Extract conference data from the DBLP XML dump.

The dump is a single ~4 GB gzipped XML file containing the entire DBLP
bibliography.  Parsing is done with a streaming SAX-style approach so the
full file is never loaded into memory.

Usage (CLI):
    uv run dblp-extract               # download + extract
    uv run dblp-extract --skip-download  # reuse existing dump

The dump URL is stable and always points to the latest monthly release:
    https://dblp.org/xml/dblp.xml.gz

XML structure of interest:
    <inproceedings key="conf/osdi/Boyd-WickizerCMPKMZ10" ...>
      <author>Silas Boyd-Wickizer</author>
      ...
      <title>An Analysis of Linux Scalability to Many Cores.</title>
      <year>2010</year>
      <booktitle>OSDI</booktitle>
      <crossref>conf/osdi/2010</crossref>
    </inproceedings>

The key attribute prefix identifies the venue; year comes from <year>.
No session structure is present in the dump, so all papers for a given
edition are grouped into a single session.
"""

from __future__ import annotations

import gzip
import logging
from collections import defaultdict
from datetime import date
from pathlib import Path

import click
import httpx
from lxml import etree
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TimeElapsedColumn,
    TransferSpeedColumn,
)

from viz_sys_conferences.models import ConferenceEdition, Paper, Session
from viz_sys_conferences.storage import save_edition

logger = logging.getLogger(__name__)
console = Console()

DUMP_URL = "https://dblp.org/xml/dblp.xml.gz"
DEFAULT_DUMP_PATH = Path("data/dblp.xml.gz")
DEFAULT_DATA_DIR = Path("data")

# DBLP key prefix → conference name
VENUE_PREFIXES: dict[str, str] = {
    "conf/osdi/": "OSDI",
    "conf/nsdi/": "NSDI",
    "conf/sosp/": "SOSP",
    "conf/eurosys/": "EuroSys",
    "conf/usenix/": "ATC",
}


def download_dump(
    dest: Path = DEFAULT_DUMP_PATH,
    force: bool = False,
) -> Path:
    """Download the DBLP XML dump, skipping if the file already exists.

    Args:
        dest: Destination path for the .gz file.
        force: Re-download even if the file already exists.

    Returns:
        Path to the downloaded file.
    """
    if dest.exists() and not force:
        size_mb = dest.stat().st_size / 1_048_576
        console.print(f"[dim]Dump already at {dest} ({size_mb:.0f} MB), skipping download.[/dim]")
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    console.print(f"Downloading DBLP dump from {DUMP_URL} …")

    with (
        httpx.Client(
            timeout=None,
            headers={"User-Agent": "viz-sys-conferences research tool"},
            follow_redirects=True,
        ) as client,
        client.stream("GET", DUMP_URL) as resp,
    ):
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0)) or None

        with Progress(
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task: TaskID = progress.add_task("Downloading", total=total)
            with dest.open("wb") as f:
                for chunk in resp.iter_bytes(chunk_size=1 << 20):  # 1 MB chunks
                    f.write(chunk)
                    progress.advance(task, len(chunk))

    size_mb = dest.stat().st_size / 1_048_576
    console.print(f"[green]Downloaded {size_mb:.0f} MB → {dest}[/green]")
    return dest


def extract_editions(
    dump_path: Path = DEFAULT_DUMP_PATH,
    start_year: int = 2006,
    end_year: int = 2026,
) -> list[ConferenceEdition]:
    """Stream-parse the DBLP dump and extract editions for the target conferences.

    Args:
        dump_path: Path to the dblp.xml.gz file.
        start_year: Earliest year to include (inclusive).
        end_year: Latest year to include (inclusive).

    Returns:
        List of ConferenceEdition objects, one per (conference, year) pair,
        each with a single session containing all papers found in the dump.
    """
    # papers[conference][year] = [Paper, ...]
    papers: dict[str, dict[int, list[Paper]]] = {
        conf: defaultdict(list) for conf in VENUE_PREFIXES.values()
    }

    console.print(f"Parsing {dump_path} …")
    n_parsed = 0

    # DBLP uses HTML entities (e.g. &uuml;) not defined in standard XML.
    # recover=True makes lxml silently skip them rather than aborting.
    opener = gzip.open if dump_path.suffix == ".gz" else open
    with opener(dump_path, "rb") as fh:
        for _event, elem in etree.iterparse(fh, events=("end",), tag="inproceedings", recover=True):
            key: str = elem.get("key", "")
            conference = _venue(key)
            if conference is None:
                elem.clear()
                continue

            year_el = elem.find("year")
            if year_el is None or not year_el.text:
                elem.clear()
                continue
            try:
                year = int(year_el.text)
            except ValueError:
                elem.clear()
                continue

            if not (start_year <= year <= end_year):
                elem.clear()
                continue

            title_el = elem.find("title")
            title = _clean(title_el.text) if title_el is not None and title_el.text else ""
            if not title:
                elem.clear()
                continue

            authors = [_clean(a.text) for a in elem.findall("author") if a.text]
            papers[conference][year].append(Paper(title=title, authors=authors))
            n_parsed += 1

            # Free memory — crucial for a 4 GB file
            elem.clear()

    console.print(f"Extracted {n_parsed} papers across {len(VENUE_PREFIXES)} venues")

    editions: list[ConferenceEdition] = []
    for conference, year_map in papers.items():
        for year in sorted(year_map):
            paper_list = year_map[year]
            url = f"https://dblp.org/db/conf/{_dblp_slug(conference)}/{_dblp_slug(conference)}{year}.html"
            editions.append(
                ConferenceEdition(
                    conference=conference,
                    year=year,
                    url=url,
                    crawled_at=date.today(),
                    sessions=[Session(title="All Papers", papers=paper_list)],
                )
            )

    editions.sort(key=lambda e: (e.conference, e.year))
    return editions


# ── CLI ──────────────────────────────────────────────────────────────────────


@click.command()
@click.option(
    "--dump",
    default=str(DEFAULT_DUMP_PATH),
    show_default=True,
    type=click.Path(),
    help="Path to store / read the dblp.xml.gz dump.",
)
@click.option(
    "--output",
    "-o",
    default=str(DEFAULT_DATA_DIR),
    show_default=True,
    type=click.Path(),
    help="Output directory for per-edition JSON files.",
)
@click.option("--start-year", default=2006, type=int, show_default=True)
@click.option("--end-year", default=2026, type=int, show_default=True)
@click.option("--skip-download", is_flag=True, help="Use existing dump file without downloading.")
@click.option("--force-download", is_flag=True, help="Re-download even if dump exists.")
def main(
    dump: str,
    output: str,
    start_year: int,
    end_year: int,
    skip_download: bool,
    force_download: bool,
) -> None:
    """Download the DBLP dump and extract systems conference data."""
    dump_path = Path(dump)
    output_dir = Path(output)

    if not skip_download:
        download_dump(dump_path, force=force_download)

    editions = extract_editions(dump_path, start_year=start_year, end_year=end_year)

    output_dir.mkdir(parents=True, exist_ok=True)
    for edition in editions:
        path = save_edition(edition, output_dir)
        console.print(
            f"[green]✓[/green] {edition.conference} {edition.year} "
            f"— {edition.paper_count} papers → {path}"
        )

    console.print(
        f"\n[bold]Done.[/bold] {len(editions)} editions, "
        f"{sum(e.paper_count for e in editions)} papers total."
    )


# ── helpers ───────────────────────────────────────────────────────────────────


def _venue(key: str) -> str | None:
    """Return conference name for a DBLP key, or None if not a target venue."""
    for prefix, conference in VENUE_PREFIXES.items():
        if key.startswith(prefix):
            return conference
    return None


_DBLP_SLUGS = {
    "OSDI": "osdi",
    "NSDI": "nsdi",
    "SOSP": "sosp",
    "EuroSys": "eurosys",
    "ATC": "usenix",
}


def _dblp_slug(conference: str) -> str:
    return _DBLP_SLUGS.get(conference, conference.lower())


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.split()).rstrip(".")
