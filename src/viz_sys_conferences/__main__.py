from __future__ import annotations

import logging
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress

from viz_sys_conferences.crawlers.dblp import DblpCrawler
from viz_sys_conferences.crawlers.eurosys import EuroSysCrawler
from viz_sys_conferences.crawlers.sosp import SospCrawler
from viz_sys_conferences.crawlers.usenix import UsenixCrawler
from viz_sys_conferences.http_client import HttpClient
from viz_sys_conferences.models import ConferenceEdition
from viz_sys_conferences.registry import ConferenceTarget, generate_targets
from viz_sys_conferences.storage import save_all_jsonl, save_edition

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

console = Console()

_USENIX_CRAWLERS = {
    "OSDI": lambda: UsenixCrawler("OSDI"),
    "NSDI": lambda: UsenixCrawler("NSDI"),
    "ATC": lambda: UsenixCrawler("ATC"),
}
_CRAWLER_MAP = {
    **_USENIX_CRAWLERS,
    "SOSP": lambda: SospCrawler(),
    "EuroSys": lambda: EuroSysCrawler(),
}

_ALL_CONFERENCES = sorted(_CRAWLER_MAP.keys())


@click.command()
@click.option(
    "--conference",
    "-c",
    multiple=True,
    type=click.Choice(_ALL_CONFERENCES + ["all"], case_sensitive=False),
    default=["all"],
    help="Conference(s) to crawl. May be repeated.",
)
@click.option("--start-year", default=2006, type=int, show_default=True)
@click.option("--end-year", default=2026, type=int, show_default=True)
@click.option(
    "--output",
    "-o",
    default="data",
    type=click.Path(),
    show_default=True,
    help="Output directory for per-edition JSON files.",
)
@click.option(
    "--jsonl",
    default=None,
    type=click.Path(),
    help="If set, also write a JSONL aggregate to this path.",
)
@click.option("--dry-run", is_flag=True, help="Print targets without crawling.")
def main(
    conference: tuple[str, ...],
    start_year: int,
    end_year: int,
    output: str,
    jsonl: str | None,
    dry_run: bool,
) -> None:
    """Crawl systems conference schedules and extract paper/session data."""
    selected = set(_ALL_CONFERENCES) if "all" in conference else set(conference)
    targets = [t for t in generate_targets(start_year, end_year) if t.conference in selected]

    if dry_run:
        for t in targets:
            console.print(f"[bold]{t.conference}[/bold] {t.year}: {t.url}")
        return

    output_dir = Path(output)
    editions: list[ConferenceEdition] = []

    with HttpClient() as client, Progress(console=console) as progress:
        task = progress.add_task("Crawling...", total=len(targets))
        for target in targets:
            progress.update(task, description=f"{target.conference} {target.year}")
            existing = output_dir / f"{target.conference}_{target.year}.json"
            if existing.exists():
                edition = ConferenceEdition.model_validate_json(existing.read_text())
                editions.append(edition)
                console.print(f"[dim]– {target.conference} {target.year} (cached)[/dim]")
                progress.advance(task)
                continue
            try:
                edition = _crawl_target(client, target)
                editions.append(edition)
                path = save_edition(edition, output_dir)
                console.print(
                    f"[green]✓[/green] {target.conference} {target.year} "
                    f"— {edition.paper_count} papers → {path}"
                )
            except Exception as exc:
                logger.warning("Failed to crawl %s %s: %s", target.conference, target.year, exc)
                console.print(f"[red]✗[/red] {target.conference} {target.year}: {exc}")
            progress.advance(task)

    if jsonl and editions:
        save_all_jsonl(editions, Path(jsonl))
        console.print(f"[blue]JSONL written to {jsonl}[/blue]")


def _crawl_target(client: HttpClient, target: ConferenceTarget) -> ConferenceEdition:
    if "dblp.org" in target.url:
        crawler = DblpCrawler(target.conference)
    else:
        crawler = _CRAWLER_MAP[target.conference]()
    result = client.fetch(target.url)
    return crawler.parse(result.html, target.url, target.year)


if __name__ == "__main__":
    main()
