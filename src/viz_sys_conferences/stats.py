"""Generate a markdown statistics table from crawled conference data."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

console = Console()


def main() -> None:
    """Read all edition JSON files and write STATS.md with a summary table."""
    data_dir = Path(__file__).parent.parent.parent / "data"
    output_path = Path(__file__).parent.parent.parent / "STATS.md"

    editions = []
    for path in sorted(data_dir.glob("*.json")):
        d = json.loads(path.read_text())
        if "conference" not in d:
            continue
        editions.append(
            {
                "conference": d["conference"],
                "year": d["year"],
                "papers": len(d["papers"]),
            }
        )

    editions.sort(key=lambda e: (e["conference"], e["year"]))

    col_conf = "Conference"
    col_papers = "Papers"

    rows = []
    for e in editions:
        yy = str(e["year"])[2:]
        rows.append((f"{e['conference']}{yy}", str(e["papers"])))

    w0 = max(len(col_conf), max(len(r[0]) for r in rows))
    w1 = max(len(col_papers), max(len(r[1]) for r in rows))

    def fmt_row(a: str, b: str) -> str:
        """Format one markdown table row with fixed column widths."""
        return f"| {a:<{w0}} | {b:>{w1}} |"

    lines = [
        "# Conference Statistics",
        "",
        fmt_row(col_conf, col_papers),
        f"| {'-' * w0} | {'-' * w1}:|",
    ]
    for row in rows:
        lines.append(fmt_row(*row))

    lines += [
        "",
        f"**Total:** {len(editions)} editions · {sum(e['papers'] for e in editions)} papers",
        "",
    ]

    output_path.write_text("\n".join(lines))
    console.print(f"Written to {output_path}")


if __name__ == "__main__":
    main()
