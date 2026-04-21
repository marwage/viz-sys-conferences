from __future__ import annotations

from dataclasses import dataclass

# EuroSys years where the standard URL pattern does not apply
_EUROSYS_URL_OVERRIDES: dict[int, str | None] = {
    2020: None,  # COVID — conference cancelled
    2021: None,  # Programme only in JS-rendered Sched embed, not scrapable
    2022: "https://2022.eurosys.org/index.html@p=494.html",
}

# SOSP years available at sigops.org (older years return 404)
# Maps year → URL path suffix
_SOSP_URL_MAP: dict[int, str] = {
    2013: "program.html",
    2015: None,   # 404
    2017: "program.html",
    2019: "program.html",
    2021: "toc.html",    # ACM DL TOC format (has abstracts)
    2023: "toc.html",    # ACM DL TOC format (has abstracts)
    2025: "schedule.html",
}

# First year where the USENIX /conference/{abbr}{YY}/technical-sessions URL exists
_USENIX_MIN_YEAR = 2012

# Last year with actual content for each USENIX conference
_USENIX_MAX_YEAR = 2025


@dataclass
class ConferenceTarget:
    """A single crawl target: one year of one conference."""

    conference: str
    year: int
    url: str


def generate_targets(start_year: int = 2006, end_year: int = 2026) -> list[ConferenceTarget]:
    """Generate crawl targets for all supported conferences.

    Args:
        start_year: First year to include (inclusive).
        end_year: Last year to include (inclusive).

    Returns:
        List of ConferenceTarget objects, one per (conference, year) pair.
    """
    targets: list[ConferenceTarget] = []
    targets.extend(_osdi_targets(start_year, end_year))
    targets.extend(_nsdi_targets(start_year, end_year))
    targets.extend(_atc_targets(start_year, end_year))
    targets.extend(_sosp_targets(start_year, end_year))
    targets.extend(_eurosys_targets(start_year, end_year))
    return targets


def _usenix_url(abbr: str, year: int) -> str:
    yy = str(year)[2:]
    return f"https://www.usenix.org/conference/{abbr}{yy}/technical-sessions"


def _osdi_targets(start: int, end: int) -> list[ConferenceTarget]:
    """OSDI: even years, URLs exist from 2012 onwards."""
    targets = []
    for year in range(max(start, _USENIX_MIN_YEAR), min(end, _USENIX_MAX_YEAR) + 1):
        if year % 2 != 0:
            continue
        targets.append(ConferenceTarget("OSDI", year, _usenix_url("osdi", year)))
    return targets


def _nsdi_targets(start: int, end: int) -> list[ConferenceTarget]:
    """NSDI: annual, URLs exist from 2012 onwards."""
    return [
        ConferenceTarget("NSDI", year, _usenix_url("nsdi", year))
        for year in range(max(start, _USENIX_MIN_YEAR), min(end, _USENIX_MAX_YEAR) + 1)
    ]


def _atc_targets(start: int, end: int) -> list[ConferenceTarget]:
    """USENIX ATC: annual, URLs exist from 2012 onwards."""
    return [
        ConferenceTarget("ATC", year, _usenix_url("atc", year))
        for year in range(max(start, _USENIX_MIN_YEAR), min(end, _USENIX_MAX_YEAR) + 1)
    ]


def _sosp_targets(start: int, end: int) -> list[ConferenceTarget]:
    """SOSP: odd years from 2013 onwards (earlier years return 404 at sigops.org)."""
    targets = []
    for year, path in _SOSP_URL_MAP.items():
        if year < start or year > end:
            continue
        if path is None:
            continue
        url = f"https://sigops.org/s/conferences/sosp/{year}/{path}"
        targets.append(ConferenceTarget("SOSP", year, url))
    return sorted(targets, key=lambda t: t.year)


def _eurosys_targets(start: int, end: int) -> list[ConferenceTarget]:
    """EuroSys: annual from 2019 (earlier subdomains do not resolve)."""
    targets = []
    for year in range(max(start, 2019), end + 1):
        if year in _EUROSYS_URL_OVERRIDES:
            url = _EUROSYS_URL_OVERRIDES[year]
            if url is None:
                continue
        elif year >= 2026:
            url = f"https://{year}.eurosys.org/preliminary-program.html"
        elif year == 2025:
            url = f"https://{year}.eurosys.org/preliminary-program.html"
        elif year >= 2023:
            url = f"https://{year}.eurosys.org/program.html"
        elif year == 2022:
            url = _EUROSYS_URL_OVERRIDES[2022]
        else:  # 2019
            url = f"https://{year}.eurosys.org/program/"
        targets.append(ConferenceTarget("EuroSys", year, url))
    return targets
