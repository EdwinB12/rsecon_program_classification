# RSECon Programme Classification

Classify RSECon conference talks by reading their abstracts from the programme PDF.

See [DATA.md](DATA.md) for details on the programme data and [RUN.md](RUN.md) for classification rules.

## Setup

```bash
uv sync
```

## Extract Session URLs

Extract Oxford Abstracts session URLs from a programme PDF:

```bash
# Print URLs to stdout
uv run python extract_session_urls.py programmes/RSECon25_Programme.pdf

# Save to a file
uv run python extract_session_urls.py programmes/RSECon25_Programme.pdf -o session_urls.txt
```
