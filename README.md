# RSECon Program Classification

Pulls accepted submissions from Oxford Abstracts for RSECon 2023, 2024, and 2025, classifies each one against a fixed scheme using the Claude API, and presents the results in a Streamlit app.

## Repository layout

```
rsecon_program_classification/
├── streamlit_app.py          ← Streamlit dashboard (run from project root)
├── classifications.csv       ← combined output, read by the app
├── CLASSIFICATIONS.md        ← the classification scheme
├── PROMPT.md                 ← system prompt template
├── src/
│   ├── pull_program.py       ← fetch program data from Oxford Abstracts
│   ├── classify_submissions.py ← classify submissions via Claude
│   └── build_csv.py          ← combine per-year JSON into one CSV
├── data/
│   ├── rsecon{23,24,25}_submissions.json     ← pulled program data
│   ├── rsecon{23,24,25}_classifications.json ← per-year Claude output
│   └── data_edits.json       ← manual submission_type overrides
├── .secrets                  ← API keys (gitignored — never commit)
├── .streamlit/config.toml    ← dashboard theme
├── pyproject.toml + uv.lock  ← dependencies (local dev)
└── requirements.txt          ← dependencies (Streamlit Cloud)
```

**All commands below should be run from the project root.** Scripts in `src/` use relative paths anchored at the project root (`data/`, `classifications.csv`, `figures/`, etc.) — running them from any other directory will fail to find the data.

## Setup

This project uses `uv` for dependency management.

```sh
uv sync
```

Create a `.secrets` file in the project root with two keys:

```
graphql_api_key = <your Oxford Abstracts API key>
claude_api_key  = <your Anthropic API key>
```

`.secrets` is gitignored — never commit it.

## Pipeline

```
                src/pull_program       src/classify_submissions      src/build_csv
Oxford Abstracts ───────────▶  data/*.json ────────────────────▶ data/*.json ──▶ classifications.csv
                  (per year)             (per year, Claude)            (combined)
                                                                           │
                                                                           └─▶ streamlit_app.py    ──▶ interactive UI
```

### 1. Pull program data

```sh
uv run python src/pull_program.py --year 2023
uv run python src/pull_program.py --year 2024
uv run python src/pull_program.py --year 2025
```

Writes `data/rsecon{YY}_submissions.json` per year, containing each accepted submission's `id`, `serial_number`, `title`, `submission_type`, and `abstract` (HTML stripped).

The script normalizes inconsistent submission-type labels across years (e.g. RSECon23 used `Poster` while 2024/25 use `Poster & Lightning Talk` — both are stored as the latter; various panel sub-flavours fold into `Panel`). The mapping lives in `SUBMISSION_TYPE_ALIASES` in [src/pull_program.py](src/pull_program.py).

### 2. Classify each submission

```sh
uv run python src/classify_submissions.py --year 2023
uv run python src/classify_submissions.py --year 2024
uv run python src/classify_submissions.py --year 2025
```

For each submission, calls the Claude API (Opus 4.7) with the categories defined in [CLASSIFICATIONS.md](CLASSIFICATIONS.md) and the prompt template in [PROMPT.md](PROMPT.md). Writes `data/rsecon{YY}_classifications.json` containing the primary category, optional secondary category, confidence (High/Medium/Low), and a short reasoning per submission.

The script saves after every row, so you can interrupt and rerun — already-classified submissions are skipped. **To force a reclassification** (e.g. after editing `CLASSIFICATIONS.md` or `PROMPT.md`), delete the corresponding `data/rsecon{YY}_classifications.json` first.

### 3. Combine into a single CSV

```sh
uv run python src/build_csv.py
```

Joins all per-year classifications into `classifications.csv` at the project root, with a `year` column. The CSV is the canonical input to the report and the dashboard.

#### Manual data edits — `data/data_edits.json`

Some submissions arrive from Oxford Abstracts with no `submission_type` set (an artifact of older event configurations). To fix those without touching the upstream data, add an entry to [data/data_edits.json](data/data_edits.json):

```json
{
  "submission_type_overrides": {
    "How do we design and deliver sustainable digital research education": "Workshop",
    "Carpentries Offline Development Hackathon": "Hackathon"
  }
}
```

`src/build_csv.py` applies these overrides on the fly when it writes the CSV — **only** when the underlying `submission_type` is empty. Existing values are never overwritten. Title matching is tolerant of trailing whitespace and trailing punctuation. The script prints a summary of how many overrides applied and lists any that didn't match a row.

The per-year `rsecon{YY}_*.json` files are not modified — `data_edits.json` is the persistent override layer applied at CSV-build time.

### 4. Run the Streamlit app locally

```sh
uv run streamlit run streamlit_app.py
```

Reads `classifications.csv` and opens an interactive browser UI for filtering by year/category/submission type, comparing across years, and searching individual submissions.

### Reproducing everything from scratch

If you've cloned the repo with no local data:

```sh
uv sync
# create .secrets with both keys (see Setup)

for year in 2023 2024 2025; do
  uv run python src/pull_program.py --year $year
  uv run python src/classify_submissions.py --year $year
done
uv run python src/build_csv.py
uv run streamlit run streamlit_app.py
```

The two API-calling steps are the slow part — pulling each year is a few seconds, classifying each year takes 5–10 minutes (~ Claude Opus 4.7 with adaptive thinking).

## Deploying to Streamlit Community Cloud

[Streamlit Community Cloud](https://share.streamlit.io) hosts public Streamlit apps for free, deployed directly from a GitHub repository. **No GitHub webhook setup is needed on your side** — Streamlit's GitHub App handles that automatically.

### One-time setup

1. **Push the repo to GitHub.** The repo must be **public** for the free tier (private repos require a paid plan).
   - `.secrets` is gitignored — never commit it.
   - Commit `classifications.csv` and the per-year JSON files in `data/` so the deployed app has data to display. The Claude API is *not* called from the app — it just visualises the CSV.

2. **Sign in at <https://share.streamlit.io>** with your GitHub account.

3. Click **"Create app"** → **"Deploy a public app from GitHub"**, then:
   - **Repository**: `EdwinB12/rsecon_program_classification` (or wherever you push it)
   - **Branch**: `master` (or `main`)
   - **Main file path**: `streamlit_app.py`
   - **App URL**: pick a subdomain — gives you `https://<your-app>.streamlit.app`

4. Streamlit Cloud installs dependencies from [requirements.txt](requirements.txt) and starts the app. First boot takes 1–2 minutes.

### What happens on push

After the initial deploy, Streamlit Cloud watches your GitHub repo via the Streamlit GitHub App (installed automatically when you authorize Streamlit in step 2). Every `git push` to the deployed branch triggers an auto-rebuild. You don't need to configure a GitHub webhook yourself — the GitHub App is the equivalent.

### Updating the data

Run the pipeline locally, commit the resulting CSV/JSON/figures, and push:

```sh
uv run python src/pull_program.py --year 2025
uv run python src/classify_submissions.py --year 2025
uv run python src/build_csv.py

git add classifications.csv data/
git commit -m "Refresh classifications for 2025"
git push
```

Streamlit Cloud picks up the change within ~30 seconds.

## Event IDs

- RSECon23: `4430`
- RSECon24: `49081`
- RSECon25: `75166`
