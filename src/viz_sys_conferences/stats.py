"""Generate a markdown statistics table from crawled conference data."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    """Read all crawled JSON editions and write STATS.md with a summary table."""
    data_dir = Path(__file__).parent.parent.parent / "data"
    output_path = Path(__file__).parent.parent.parent / "STATS.md"

    editions = []
    for path in sorted(data_dir.glob("*.json")):
        d = json.loads(path.read_text())
        editions.append(
            {
                "conference": d["conference"],
                "year": d["year"],
                "sessions": len(d["sessions"]),
                "papers": sum(len(s["papers"]) for s in d["sessions"]),
            }
        )

    # Sort by conference name then year
    editions.sort(key=lambda e: (e["conference"], e["year"]))

    col_conf = "Conference"
    col_sessions = "Sessions"
    col_papers = "Papers"

    # Build rows
    rows = []
    for e in editions:
        yy = str(e["year"])[2:]
        label = f"{e['conference']}{yy}"
        rows.append((label, str(e["sessions"]), str(e["papers"])))

    # Column widths
    w0 = max(len(col_conf), max(len(r[0]) for r in rows))
    w1 = max(len(col_sessions), max(len(r[1]) for r in rows))
    w2 = max(len(col_papers), max(len(r[2]) for r in rows))

    def fmt_row(a: str, b: str, c: str) -> str:
        """Format one markdown table row with fixed column widths."""
        return f"| {a:<{w0}} | {b:>{w1}} | {c:>{w2}} |"

    lines = [
        "# Conference Statistics",
        "",
        fmt_row(col_conf, col_sessions, col_papers),
        f"| {'-' * w0} | {'-' * w1}:| {'-' * w2}:|",
    ]
    for row in rows:
        lines.append(fmt_row(*row))

    lines += [
        "",
        f"**Total:** {len(editions)} editions · "
        f"{sum(e['sessions'] for e in editions)} sessions · "
        f"{sum(e['papers'] for e in editions)} papers",
        "",
    ]

    output_path.write_text("\n".join(lines))
    print(f"Written to {output_path}")


if __name__ == "__main__":
    main()
