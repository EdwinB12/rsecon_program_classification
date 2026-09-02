"""Pull accepted submissions for an RSECon year from Oxford Abstracts.

For each accepted, non-archived submission, extracts:
  - title  (plain text, no HTML)
  - submission type  (accepted_for.value)
  - abstract  (response to the "Abstract" question)

Output: data/rsecon{YY}_submissions.json

Usage (run from the project root):
    uv run python src/pull_program.py [--year 2023|2024|2025]   (default: 2025)
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ENDPOINT = "https://app.oxfordabstracts.com/v1/graphql"
EVENT_IDS = {2023: 4430, 2024: 49081, 2025: 75166, 2026: 76908}
SECRETS_PATH = Path(".secrets")
DATA_DIR = Path("data")

# Normalize submission-type labels across years.
#   - RSECon23 used "Poster"; 2024/25 use "Poster & Lightning Talk" — canonicalize on the newer label.
#   - Various sub-flavours of panel ("Panel (Audience-Led)", "Panel (Presenter-Led)") are folded into "Panel".
SUBMISSION_TYPE_ALIASES = {
    "Poster": "Poster & Lightning Talk",
    "Panel (Audience-Led)": "Panel",
    "Panel (Presenter-Led)": "Panel",
    "Invited": "Panel",
}


def normalize_submission_type(value: str | None) -> str | None:
    if value is None:
        return None
    return SUBMISSION_TYPE_ALIASES.get(value, value)

QUERY = """
query FetchSubmissions($event_id: Int!) {
  events_by_pk(id: $event_id) {
    id
    submissions(
      where: {decision: {value: {_eq: "Accepted"}}, archived: {_eq: false}}
    ) {
      id
      serial_number
      title { without_html }
      accepted_for { value }
      responses {
        value
        question { question_name }
      }
    }
  }
}
"""


def load_api_key() -> str:
    text = SECRETS_PATH.read_text()
    m = re.search(
        r"""graphql_api_key\s*=\s*['"]?([^'"\s]+)""",
        text,
        re.IGNORECASE,
    )
    if not m:
        raise SystemExit(f"graphql_api_key not found in {SECRETS_PATH}")
    return m.group(1)


def post(query: str, variables: dict, key: str) -> dict:
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Content-Type": "application/json", "x-api-key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(f"HTTP {e.code}: {body}")


class _HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag in {"p", "br", "div", "li", "tr"}:
            self._chunks.append("\n")

    def get_text(self) -> str:
        return "".join(self._chunks)


def strip_html(s: str | None) -> str | None:
    if not s:
        return s
    p = _HTMLStripper()
    p.feed(s)
    text = html.unescape(p.get_text())
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_abstract(responses: list[dict]) -> str | None:
    for r in responses or []:
        q = (r.get("question") or {}).get("question_name") or ""
        if q.strip().lower() == "abstract":
            return strip_html(r.get("value"))
    return None


def first_title(title_field) -> str | None:
    # `title` is a list of title_responses
    if not title_field:
        return None
    if isinstance(title_field, list):
        return (title_field[0] or {}).get("without_html")
    return title_field.get("without_html")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--year", type=int, choices=sorted(EVENT_IDS), default=2025
    )
    args = parser.parse_args()

    event_id = EVENT_IDS[args.year]
    DATA_DIR.mkdir(exist_ok=True)
    output_path = DATA_DIR / f"rsecon{args.year % 100:02d}_submissions.json"

    key = load_api_key()
    body = post(QUERY, {"event_id": event_id}, key)

    if "errors" in body:
        print("GraphQL errors:", json.dumps(body["errors"], indent=2), file=sys.stderr)
        return 1

    event = (body.get("data") or {}).get("events_by_pk")
    if not event:
        print(f"No event found for id {event_id} (year {args.year})", file=sys.stderr)
        return 1

    rows = []
    for sub in event.get("submissions", []):
        rows.append(
            {
                "id": sub.get("id"),
                "serial_number": sub.get("serial_number"),
                "title": first_title(sub.get("title")),
                "submission_type": normalize_submission_type(
                    (sub.get("accepted_for") or {}).get("value")
                ),
                "abstract": extract_abstract(sub.get("responses") or []),
            }
        )

    output_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    print(f"Wrote {len(rows)} submissions to {output_path}")

    types: dict[str, int] = {}
    for r in rows:
        t = r["submission_type"] or "(none)"
        types[t] = types.get(t, 0) + 1
    print("\nBy submission type:")
    for t, n in sorted(types.items(), key=lambda x: -x[1]):
        print(f"  {n:4d}  {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
