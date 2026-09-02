"""Classify RSECon submissions for a given year using the Claude API.

Reads:
  - .secrets                              (key: claude_api_key)
  - PROMPT.md                             (system prompt template)
  - CLASSIFICATIONS.md                    (the classification scheme)
  - data/rsecon{YY}_submissions.json

Writes:
  - data/rsecon{YY}_classifications.json

Usage (run from the project root):
    uv run python src/classify_submissions.py [--year 2023|2024|2025]   (default: 2025)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel, Field

MODEL = "claude-opus-4-7"
YEARS = [2023, 2024, 2025, 2026]
SECRETS_PATH = Path(".secrets")
PROMPT_PATH = Path("PROMPT.md")
CLASSIFICATIONS_PATH = Path("CLASSIFICATIONS.md")
DATA_DIR = Path("data")

PrimaryCategory = Literal["Software", "Research", "Community", "Other"]
SecondaryCategory = Literal["Software", "Research", "Community", "Other", "N/A"]
Confidence = Literal["High", "Medium", "Low"]


class Classification(BaseModel):
    reasoning: str = Field(
        description="One- or two-sentence justification grounded in the abstract."
    )
    primary_category: PrimaryCategory = Field(
        description="The dominant category for the submission."
    )
    secondary_category: SecondaryCategory = Field(
        description="A meaningful secondary category, or 'N/A' if the submission falls clearly into the primary topic."
    )
    confidence: Confidence = Field(
        description="Confidence in the primary classification. High = clear-cut. Medium = leans one way but defensible. Low = genuinely ambiguous."
    )


def load_api_key() -> str:
    text = SECRETS_PATH.read_text()
    m = re.search(r"""claude_api_key\s*=\s*['"]?([^'"\s]+)""", text, re.IGNORECASE)
    if not m:
        raise SystemExit(f"claude_api_key not found in {SECRETS_PATH}")
    return m.group(1)


def build_system_prompt() -> str:
    template = PROMPT_PATH.read_text()
    categories = CLASSIFICATIONS_PATH.read_text().strip()
    return template.format(categories=categories)


def classify_one(
    client: anthropic.Anthropic, system: str, title: str, abstract: str
) -> Classification:
    user_content = f"TITLE: {title}\n\nABSTRACT:\n{abstract}"
    response = client.messages.parse(
        model=MODEL,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=system,
        messages=[{"role": "user", "content": user_content}],
        output_format=Classification,
    )
    return response.parsed_output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, choices=YEARS, default=2025)
    args = parser.parse_args()

    yy = args.year % 100
    DATA_DIR.mkdir(exist_ok=True)
    input_path = DATA_DIR / f"rsecon{yy:02d}_submissions.json"
    output_path = DATA_DIR / f"rsecon{yy:02d}_classifications.json"

    api_key = load_api_key()
    system = build_system_prompt()
    rows = json.loads(input_path.read_text())

    client = anthropic.Anthropic(api_key=api_key)

    results: list[dict] = []
    if output_path.exists():
        try:
            results = json.loads(output_path.read_text())
            done_ids = {r["id"] for r in results}
            print(f"Resuming {output_path} — {len(done_ids)} already classified.")
        except Exception:
            results = []
            done_ids = set()
    else:
        done_ids = set()

    pending = [r for r in rows if r["id"] not in done_ids]
    print(f"Classifying {len(pending)} of {len(rows)} submissions for {args.year} with {MODEL}.\n")

    for i, sub in enumerate(pending, 1):
        try:
            cls = classify_one(client, system, sub["title"], sub["abstract"])
        except anthropic.APIStatusError as e:
            print(
                f"  [{i}/{len(pending)}] id={sub['id']}: API error {e.status_code}: {e.message}",
                file=sys.stderr,
            )
            continue

        results.append(
            {
                "id": sub["id"],
                "serial_number": sub["serial_number"],
                "title": sub["title"],
                "submission_type": sub["submission_type"],
                "primary_category": cls.primary_category,
                "secondary_category": cls.secondary_category,
                "confidence": cls.confidence,
                "reasoning": cls.reasoning,
            }
        )

        # Save after every row so a crash never loses progress.
        output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
        sec = "" if cls.secondary_category == "N/A" else f" / {cls.secondary_category}"
        print(
            f"  [{i}/{len(pending)}] id={sub['id']} → {cls.primary_category}{sec} ({cls.confidence})  {sub['title'][:60]}"
        )

    # Summary
    print(f"\nWrote {len(results)} classifications to {output_path}\n")

    primary: dict[str, int] = {}
    primary_conf: dict[tuple[str, str], int] = {}
    secondary: dict[str, int] = {}
    for r in results:
        primary[r["primary_category"]] = primary.get(r["primary_category"], 0) + 1
        secondary[r["secondary_category"]] = secondary.get(r["secondary_category"], 0) + 1
        key = (r["primary_category"], r["confidence"])
        primary_conf[key] = primary_conf.get(key, 0) + 1

    print("By primary category:")
    for cat, n in sorted(primary.items(), key=lambda x: -x[1]):
        print(f"  {n:4d}  {cat}")

    print("\nBy primary category × confidence:")
    for cat in ["Software", "Research", "Community", "Other"]:
        for conf in ["High", "Medium", "Low"]:
            n = primary_conf.get((cat, conf), 0)
            if n:
                print(f"  {cat:10s} {conf:6s} {n}")

    print("\nBy secondary category:")
    for cat, n in sorted(secondary.items(), key=lambda x: -x[1]):
        print(f"  {n:4d}  {cat}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
