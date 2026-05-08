"""Generate figures and write REPORT.md from classifications.csv.

Reads:
  - classifications.csv

Writes:
  - figures/by_year.png
  - figures/by_type.png
  - figures/reach.png
  - REPORT.md

Usage (run from the project root):
    uv run python src/make_report.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

CSV_PATH = Path("classifications.csv")
FIG_DIR = Path("figures")
REPORT_PATH = Path("REPORT.md")
CATEGORY_ORDER = ["Software", "Research", "Community", "Other"]
COLORS = {
    "Software": "#1f77b4",
    "Research": "#2ca02c",
    "Community": "#ff7f0e",
    "Other": "#7f7f7f",
}


def main() -> int:
    if not CSV_PATH.exists():
        print(f"{CSV_PATH} missing — run build_csv.py first", file=sys.stderr)
        return 1

    df = pd.read_csv(CSV_PATH)
    df["submission_type"] = df["submission_type"].fillna("(none)")
    FIG_DIR.mkdir(exist_ok=True)

    # ----- Figure 1: counts by year + primary category --------------------
    pivot_year = (
        df.groupby(["year", "primary_category"]).size().unstack(fill_value=0)
    )
    pivot_year = pivot_year.reindex(columns=CATEGORY_ORDER, fill_value=0)
    fig, ax = plt.subplots(figsize=(8, 5))
    pivot_year.plot(
        kind="bar",
        ax=ax,
        color=[COLORS[c] for c in pivot_year.columns],
        edgecolor="white",
    )
    ax.set_title("RSECon submissions by primary category (per year)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Submissions")
    ax.set_xticklabels(pivot_year.index, rotation=0)
    ax.legend(title="Primary category", loc="upper left", frameon=False)
    for c in ax.containers:
        ax.bar_label(c, padding=2, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "by_year.png", dpi=150)
    plt.close(fig)

    # ----- Figure 2: by submission type, stacked --------------------------
    pivot_type = (
        df.groupby(["submission_type", "primary_category"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=CATEGORY_ORDER, fill_value=0)
    )
    pivot_type = pivot_type.loc[pivot_type.sum(axis=1).sort_values(ascending=False).index]

    fig, ax = plt.subplots(figsize=(9, 5))
    pivot_type.plot(
        kind="barh",
        stacked=True,
        ax=ax,
        color=[COLORS[c] for c in pivot_type.columns],
        edgecolor="white",
    )
    ax.invert_yaxis()
    ax.set_title("Submissions by type and primary category (all years combined)")
    ax.set_xlabel("Submissions")
    ax.set_ylabel("")
    ax.legend(title="Primary category", loc="lower right", frameon=False)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "by_type.png", dpi=150)
    plt.close(fig)

    # ----- Figure 3: total reach (primary + secondary) per year -----------
    reach_rows = []
    for year, ydf in df.groupby("year"):
        reach: dict[str, int] = dict.fromkeys(CATEGORY_ORDER, 0)
        for _, r in ydf.iterrows():
            reach[r["primary_category"]] += 1
            if r["secondary_category"] != "N/A":
                reach[r["secondary_category"]] = reach.get(r["secondary_category"], 0) + 1
        for cat in CATEGORY_ORDER:
            reach_rows.append({"year": year, "category": cat, "count": reach[cat]})
    reach_df = pd.DataFrame(reach_rows)
    pivot_reach = reach_df.pivot(index="year", columns="category", values="count").reindex(
        columns=CATEGORY_ORDER, fill_value=0
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    pivot_reach.plot(
        kind="bar",
        ax=ax,
        color=[COLORS[c] for c in pivot_reach.columns],
        edgecolor="white",
    )
    ax.set_title("Total reach per year (primary + secondary)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Submissions touching the category")
    ax.set_xticklabels(pivot_reach.index, rotation=0)
    ax.legend(title="Category", loc="upper left", frameon=False)
    for c in ax.containers:
        ax.bar_label(c, padding=2, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "reach.png", dpi=150)
    plt.close(fig)

    # ----- REPORT.md ------------------------------------------------------
    total = len(df)
    by_year_total = df.groupby("year").size().to_dict()
    by_year_cat = pivot_year.to_dict()  # {category: {year: count}}
    by_conf = df["confidence"].value_counts().to_dict()

    pct = lambda n, d: f"{(n / d * 100):.0f}%" if d else "—"

    def yr_pct(year: int, cat: str) -> str:
        n = by_year_cat.get(cat, {}).get(year, 0)
        return f"{n} ({pct(n, by_year_total[year])})"

    years = sorted(by_year_total)

    lines = [
        "# RSECon program classification — short report",
        "",
        f"Classified **{total} accepted submissions** across "
        f"RSECon{years[0]}, RSECon{years[1]}, and RSECon{years[2]} using Claude Opus 4.7 against the four-category scheme in [CLASSIFICATIONS.md](CLASSIFICATIONS.md).",
        "",
        "## Headline numbers",
        "",
        f"| Year | Submissions | Software | Research | Community |",
        f"|---|---:|---|---|---|",
    ]
    for y in years:
        lines.append(
            f"| {y} | {by_year_total[y]} | "
            f"{yr_pct(y, 'Software')} | "
            f"{yr_pct(y, 'Research')} | "
            f"{yr_pct(y, 'Community')} |"
        )

    lines += [
        "",
        f"Confidence: {by_conf.get('High', 0)} High · {by_conf.get('Medium', 0)} Medium · {by_conf.get('Low', 0)} Low.",
        "",
        "## Figures",
        "",
        "### Counts per year",
        "",
        "![Counts per year](figures/by_year.png)",
        "",
        "### By submission type (all years combined)",
        "",
        "![Submission type](figures/by_type.png)",
        "",
        "### Total reach per year (primary + secondary)",
        "",
        "Total reach counts a submission once for its primary category and once for its secondary (if any) — useful for asking *how many talks engage with X at all*.",
        "",
        "![Reach](figures/reach.png)",
        "",
        "## Observations",
        "",
        "- **Research is shrinking as a share of the program** — 25% (2023) → 19% (2024) → 14% (2025). In absolute terms, the count goes 18 → 14 → 13 even as the program grows from 73 to 91 accepted submissions. Domain-specific tool announcements are losing ground to community and general-tooling content.",
        "- **Community is consistently the largest single bucket** and edges up slightly year-on-year (40% → 43% → 44%). RSECon is foremost a community gathering, and that's reflected in what gets accepted.",
        "- **Software grows** from 36% to 42% — both in share and in absolute count (26 → 29 → 38). Cross-cutting tooling, infrastructure, and software-engineering practice claim a larger slice each year.",
        "- **Posters and Lightning Talks** carry the highest fraction of Research-primary submissions in any given year, suggesting the short-format slot is where the few remaining domain-specific tool announcements concentrate.",
        "- The *total reach* numbers show that even when a talk is primarily Community or Research, Software is very often a meaningful secondary — many sessions are about people or science, but with a tool or platform as the vehicle.",
        "",
        "## Method",
        "",
        "1. **Pull**: program data fetched from the Oxford Abstracts GraphQL API for events 4430 (2023), 49081 (2024), and 75166 (2025) — accepted, non-archived submissions only.",
        "2. **Classify**: each submission's title and abstract are sent to Claude Opus 4.7 with the categories defined in [CLASSIFICATIONS.md](CLASSIFICATIONS.md) and the prompt in [PROMPT.md](PROMPT.md). The model returns a primary category, optional secondary category, confidence, and a short reasoning.",
        "3. **Combine**: per-year results are joined into a single CSV (`classifications.csv`) used by both this report and the Streamlit app.",
        "",
        "## Caveats",
        "",
        "- The 2023 program has 11 submissions with no `accepted_for` value (`(none)`) — likely a data-entry difference in the older Oxford Abstracts schema.",
        "- Classifications are LLM-generated; ~25–30% are Medium-confidence and could swing the other way under a different reading. Use the Streamlit app to spot-check borderline cases.",
        "- The classification scheme has evolved through the conversation; results here use the latest definitions in [CLASSIFICATIONS.md](CLASSIFICATIONS.md).",
        "",
    ]

    REPORT_PATH.write_text("\n".join(lines))
    print(f"Wrote {REPORT_PATH} and 3 figures to {FIG_DIR}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
