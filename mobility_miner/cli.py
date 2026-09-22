"""Command-line entry point for mobility evidence extraction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from .report import write_html_report
from .sources import iter_local_inputs, parse_local_path, parse_url


def iter_records(inputs: list[str], pages: int | None, max_chars: int | None):
    """Yield records from local paths, directories, and URLs."""
    for item in inputs:
        if item.startswith(("http://", "https://")):
            yield from parse_url(item, pages=pages, max_chars=max_chars)
        else:
            for path in iter_local_inputs([item]):
                yield from parse_local_path(path, pages=pages, max_chars=max_chars)


def write_jsonl(records: Iterable[dict], output: Path) -> int:
    """Write records without discarding paragraph-level evidence alignment."""
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract evidence-linked charge-carrier mobility records.")
    parser.add_argument("inputs", nargs="+", help="PDF, HTML, XML, text files, directories, or URLs.")
    parser.add_argument("-o", "--output", type=Path, required=True, help="JSONL output path.")
    parser.add_argument("--html-output", type=Path, help="Optional standalone HTML review report.")
    parser.add_argument("--pages", type=int, default=0, help="PDF pages to parse; 0 means all pages.")
    parser.add_argument("--max-chars", type=int, default=0, help="Text cap per input; 0 means no cap.")
    parser.add_argument("--values-only", action="store_true", help="Drop method-only candidates with no mobility value.")
    args = parser.parse_args()

    records = list(
        iter_records(
            args.inputs,
            pages=args.pages or None,
            max_chars=args.max_chars or None,
        )
    )
    if args.values_only:
        records = [record for record in records if record.get("passes_mobility_filter")]
    count = write_jsonl(records, args.output)
    print("wrote {} mobility records to {}".format(count, args.output))
    if args.html_output:
        write_html_report(records, args.html_output, jsonl_path=args.output)
        print("wrote HTML report to {}".format(args.html_output))


if __name__ == "__main__":
    main()
