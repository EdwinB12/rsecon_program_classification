"""Combine per-year classifications into a single CSV.

Reads:
  - data/rsecon{YY}_classifications.json   for each year present
  - data/rsecon{YY}_submissions.json       (to recover the abstract for the CSV)
  - data/data_edits.json                   (optional manual overrides — see README)

Writes:
  - classifications.csv   (project root)

Usage (run from the project root):
    uv run python src/build_csv.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

YEARS = [2023, 2024, 2025, 2026]
DATA_DIR = Path("data")
OUTPUT_PATH = Path("classifications.csv")
EDITS_PATH = DATA_DIR / "data_edits.json"
COLUMNS = [
    "year",
    "id",
    "serial_number",
    "title",
    "submission_type",
    "primary_category",
    "secondary_category",
    "confidence",
    "reasoning",
    "abstract",
]


def _normalize_title(t: str) -> str:
    """Match titles tolerantly — strip whitespace and trailing punctuation."""
    return (t or "").strip().rstrip(".").strip()


def load_edits() -> dict[str, str]:
    """Return {normalized_title: submission_type} from data_edits.json (or empty)."""
    if not EDITS_PATH.exists():
        return {}
    raw = json.loads(EDITS_PATH.read_text()).get("submission_type_overrides", {})
    return {_normalize_title(k): v for k, v in raw.items()}


def main() -> int:
    edits = load_edits()
    edits_used: set[str] = set()

    rows: list[dict] = []
    for year in YEARS:
        yy = year % 100
        cls_path = DATA_DIR / f"rsecon{yy:02d}_classifications.json"
        subs_path = DATA_DIR / f"rsecon{yy:02d}_submissions.json"
        if not cls_path.exists():
            print(f"skip {year}: {cls_path} missing", file=sys.stderr)
            continue

        cls_rows = json.loads(cls_path.read_text())
        abstracts: dict[int, str] = {}
        if subs_path.exists():
            for s in json.loads(subs_path.read_text()):
                abstracts[s["id"]] = s.get("abstract") or ""

        for r in cls_rows:
            stype = r["submission_type"] or ""
            if not stype:
                key = _normalize_title(r["title"])
                if key in edits:
                    stype = edits[key]
                    edits_used.add(key)

            rows.append(
                {
                    "year": year,
                    "id": r["id"],
                    "serial_number": r["serial_number"],
                    "title": r["title"],
                    "submission_type": stype,
                    "primary_category": r["primary_category"],
                    "secondary_category": r["secondary_category"],
                    "confidence": r["confidence"],
                    "reasoning": r["reasoning"],
                    "abstract": abstracts.get(r["id"], ""),
                }
            )

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")
    by_year: dict[int, int] = {}
    for r in rows:
        by_year[r["year"]] = by_year.get(r["year"], 0) + 1
    for y in sorted(by_year):
        print(f"  {y}: {by_year[y]} submissions")

    if edits:
        unmatched = sorted(set(edits) - edits_used)
        still_missing = sum(1 for r in rows if not r["submission_type"])
        print(
            f"\nEdits: {len(edits_used)}/{len(edits)} applied"
            f" — {still_missing} rows still have no submission_type"
        )
        for k in unmatched:
            print(f"  unmatched edit: {k!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
