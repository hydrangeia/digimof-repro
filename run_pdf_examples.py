"""Run DigiMOF parsers on PDF files via pdfminer text extraction.

The original DigiMOF entry point is designed for HTML/XML. This helper keeps the
legacy parser stack, but uses pdfminer.six to convert PDFs into paragraphs first.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pdfminer.high_level import extract_text

from chemdataextractor import Document
from chemdataextractor.doc import Paragraph
from MOF_database import reobj


OBVIOUS_FALSE_MOF_NAMES = {
    "ML",
}


def iter_pdfs(path: Path):
    if path.is_file() and path.suffix.lower() == ".pdf":
        yield path
    elif path.is_dir():
        yield from sorted(path.rglob("*.pdf"))


def split_paragraphs(text: str, max_chars: int | None = None):
    if max_chars:
        text = text[:max_chars]
    chunks = re.split(r"\n\s*\n+", text)
    for chunk in chunks:
        paragraph = " ".join(chunk.split())
        if len(paragraph) >= 40:
            yield paragraph


def is_mof_record(record: dict) -> bool:
    names = record.get("names") or []
    return any(name not in OBVIOUS_FALSE_MOF_NAMES and re.search(reobj, name) for name in names)


def normalize_record(pdf: Path, paragraph: str, record: dict) -> dict:
    data = {
        "source_file": str(pdf),
        "source_paragraph": paragraph,
        "record": record,
    }
    if is_mof_record(record):
        mof_data = {
            "file": str(pdf),
            "compound": {"Compound": {"names": record.get("names", [])}},
        }
        if record.get("synthesis_routes"):
            mof_data["synthesis_route"] = record["synthesis_routes"]
        if record.get("topologies"):
            first_topology = record["topologies"][0]
            mof_data["topology"] = first_topology.get("abrv")
        if record.get("linker_routes"):
            mof_data["linker"] = record["linker_routes"]
        data["MOF_data"] = mof_data
    return data


def parse_pdf(pdf: Path, pages: int | None = None, max_chars: int | None = None):
    page_numbers = range(pages) if pages else None
    text = extract_text(str(pdf), page_numbers=page_numbers)
    for paragraph in split_paragraphs(text, max_chars=max_chars):
        doc = Document(Paragraph(paragraph))
        for record in doc.records.serialize():
            if record:
                yield normalize_record(pdf, paragraph, record)


def main():
    parser = argparse.ArgumentParser(description="Run DigiMOF parser rules on PDFs.")
    parser.add_argument("input", type=Path, help="PDF file or directory containing PDFs.")
    parser.add_argument("output", type=Path, help="JSONL output path.")
    parser.add_argument("--pages", type=int, default=3, help="Number of pages to parse from each PDF.")
    parser.add_argument("--max-chars", type=int, default=None, help="Optional character limit after PDF text extraction.")
    parser.add_argument("--mof-only", action="store_true", help="Only write records that pass DigiMOF MOF-name filtering.")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with args.output.open("w", encoding="utf-8") as handle:
        for pdf in iter_pdfs(args.input):
            for item in parse_pdf(pdf, pages=args.pages, max_chars=args.max_chars):
                if args.mof_only and "MOF_data" not in item:
                    continue
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
                total += 1
    print("wrote {} records to {}".format(total, args.output))


if __name__ == "__main__":
    main()
