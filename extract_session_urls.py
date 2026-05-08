"""Extract Oxford Abstracts session URLs from an RSECon programme PDF."""

import argparse
import re
import sys
from pathlib import Path

import pymupdf


def extract_session_urls(pdf_path: Path) -> list[str]:
    """Extract Oxford Abstracts session URLs from a programme PDF."""
    doc = pymupdf.open(pdf_path)
    urls = set()

    for page in doc:
        for link in page.get_links():
            uri = link.get("uri", "")
            if "virtual.oxfordabstracts.com" in uri:
                urls.add(uri)

        for match in re.findall(r"https?://virtual\.oxfordabstracts\.com/[^\s)<>\"]+", page.get_text()):
            urls.add(match)

    doc.close()
    return sorted(urls)


def main():
    parser = argparse.ArgumentParser(description="Extract Oxford Abstracts session URLs from an RSECon programme PDF.")
    parser.add_argument("pdf", type=Path, help="Path to the programme PDF")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output file (default: stdout)")
    args = parser.parse_args()

    if not args.pdf.exists():
        print(f"Error: {args.pdf} not found", file=sys.stderr)
        sys.exit(1)

    urls = extract_session_urls(args.pdf)

    if args.output:
        args.output.write_text("\n".join(urls) + "\n", encoding="utf-8")
        print(f"Saved {len(urls)} URLs to {args.output}")
    else:
        for url in urls:
            print(url)


if __name__ == "__main__":
    main()
