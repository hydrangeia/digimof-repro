"""Print PDF sentences containing selected terms."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from pdfminer.high_level import extract_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("terms", nargs="+")
    parser.add_argument("--pages", type=int, default=None)
    parser.add_argument("--context", type=int, default=0)
    args = parser.parse_args()

    page_numbers = range(args.pages) if args.pages else None
    text = extract_text(str(args.pdf), page_numbers=page_numbers)
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    patterns = [re.compile(term, re.I) for term in args.terms]
    printed = set()
    for i, sentence in enumerate(parts):
        if any(pattern.search(sentence) for pattern in patterns):
            start = max(0, i - args.context)
            end = min(len(parts), i + args.context + 1)
            snippet = " ".join(parts[start:end])
            snippet = snippet.encode("ascii", "ignore").decode("ascii")
            if snippet not in printed:
                printed.add(snippet)
                print("---")
                print(snippet[:1600])


if __name__ == "__main__":
    main()
