"""Classify local PDFs for DigiMOF/COF-style extraction relevance."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from pdfminer.high_level import extract_text


RELATED_PATTERNS = [
    r"\bcovalent organic framework",
    r"\bCOFs?\b",
    r"\bmetal[- ]organic framework",
    r"\bMOFs?\b",
    r"\bZIF[- ]?\d",
    r"\bMIL[- ]?\d",
    r"\bDUT[- ]?\d",
]

EXPERIMENT_PATTERNS = [
    r"\bsynthesi[sz]ed\b",
    r"\bprepared\b",
    r"\bfabricated\b",
    r"\bsolvothermal\b",
    r"\bhydrothermal\b",
    r"\bmechanochemical\b",
    r"\bexperimental section\b",
    r"\bmaterials and methods\b",
    r"\breagents\b",
    r"\bcharacteri[sz]ation\b",
    r"\bpowder x-ray diffraction\b",
    r"\bPXRD\b",
]

COMPUTATIONAL_PATTERNS = [
    r"\bdensity functional theory\b",
    r"\bDFT\b",
    r"\bfirst[- ]principles\b",
    r"\bab initio\b",
    r"\bmolecular dynamics\b",
    r"\bmachine learning\b",
    r"\bhigh[- ]throughput screening\b",
    r"\bcomputed\b",
    r"\bsimulation\b",
]

REVIEW_PATTERNS = [
    r"\breview\b",
    r"\bperspective\b",
    r"\bintroduction\b",
]


def count_patterns(text: str, patterns: list[str]) -> int:
    return sum(len(re.findall(pattern, text, flags=re.I)) for pattern in patterns)


def clean_snippet(text: str, length: int = 260) -> str:
    text = " ".join(text.split())
    return text[:length]


def classify_pdf(path: Path, pages: int) -> dict[str, str | int]:
    try:
        text = extract_text(str(path), page_numbers=range(pages))
    except Exception as exc:
        return {
            "file": str(path),
            "category": "read_error",
            "related_score": 0,
            "experiment_score": 0,
            "computational_score": 0,
            "review_score": 0,
            "is_si": int("SI -" in path.name or "ESI" in path.name or "MOESM" in path.name),
            "snippet": "{}".format(exc),
        }

    related_score = count_patterns(path.name + "\n" + text, RELATED_PATTERNS)
    experiment_score = count_patterns(text, EXPERIMENT_PATTERNS)
    computational_score = count_patterns(path.name + "\n" + text, COMPUTATIONAL_PATTERNS)
    review_score = count_patterns(path.name + "\n" + text, REVIEW_PATTERNS)
    is_si = int("SI -" in path.name or "ESI" in path.name or "MOESM" in path.name)

    if not related_score:
        category = "not_mof_cof"
    elif is_si and experiment_score:
        category = "related_si_experimental"
    elif experiment_score >= 2 and experiment_score >= computational_score:
        category = "related_experimental_candidate"
    elif computational_score >= 2:
        category = "related_computational_or_theory"
    elif review_score >= 2:
        category = "related_review_or_method"
    else:
        category = "related_unclear"

    return {
        "file": str(path),
        "category": category,
        "related_score": related_score,
        "experiment_score": experiment_score,
        "computational_score": computational_score,
        "review_score": review_score,
        "is_si": is_si,
        "snippet": clean_snippet(text),
    }


def iter_pdfs(root: Path):
    yield from sorted(root.rglob("*.pdf"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pages", type=int, default=2)
    args = parser.parse_args()

    rows = [classify_pdf(path, args.pages) for path in iter_pdfs(args.root)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["file"])
        writer.writeheader()
        writer.writerows(rows)

    for row in rows:
        if row["category"] != "not_mof_cof":
            print(
                "{category}\tR={related_score} E={experiment_score} C={computational_score} SI={is_si}\t{file}".format(
                    **row
                )
            )


if __name__ == "__main__":
    main()
