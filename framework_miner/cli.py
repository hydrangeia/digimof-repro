"""Command line entry point for normalized framework extraction."""

from __future__ import annotations

import argparse
from pathlib import Path

from .legacy_digimof import iter_local_inputs, merge_items, parse_local_path, parse_url, write_jsonl


def iter_records(inputs: list[str], pages: int | None, max_chars: int | None, framework: str):
    for item in inputs:
        if item.startswith(("http://", "https://")):
            yield from parse_url(item, pages=pages, max_chars=max_chars, framework=framework)
        else:
            for path in iter_local_inputs([item]):
                yield from parse_local_path(path, pages=pages, max_chars=max_chars, framework=framework)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract normalized framework records.")
    parser.add_argument("inputs", nargs="+", help="Files, directories, or URLs.")
    parser.add_argument("-o", "--output", type=Path, required=True, help="JSONL output path.")
    parser.add_argument("--framework", choices=["mof", "cof", "all"], default="mof", help="Framework parser to run.")
    parser.add_argument("--pages", type=int, default=2, help="PDF pages to parse per file. Use 0 for all pages.")
    parser.add_argument("--max-chars", type=int, default=8000, help="Optional text cap per PDF. Use 0 for no cap.")
    parser.add_argument("--mof-only", action="store_true", help="Write only records that pass DigiMOF MOF-name filtering.")
    parser.add_argument("--framework-only", action="store_true", help="Write only records that pass the selected framework filter.")
    parser.add_argument("--no-merge", action="store_true", help="Keep raw parser records instead of merging records from the same evidence paragraph.")
    args = parser.parse_args()

    pages = args.pages if args.pages else None
    max_chars = args.max_chars if args.max_chars else None
    records = iter_records(args.inputs, pages=pages, max_chars=max_chars, framework=args.framework)
    if not args.no_merge:
        records = merge_items(records)
    count = write_jsonl(records, args.output, mof_only=args.mof_only, framework_only=args.framework_only)
    print("wrote {} records to {}".format(count, args.output))


if __name__ == "__main__":
    main()
