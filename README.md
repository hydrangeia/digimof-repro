# Framework Miner for MOF/COF Synthesis Literature

Framework Miner is an auditable literature-mining prototype for extracting
MOF and COF synthesis information from open-access papers, local PDFs, HTML
pages, and DOI/URL batches.

The project began as a reproducibility branch around the DigiMOF database code
and has since grown a lightweight, evidence-first extraction layer for both
metal-organic frameworks (MOFs) and covalent organic frameworks (COFs). Its main
goal is not to replace expert reading. Its goal is to make paper reading,
benchmarking, and database curation faster and more reproducible by showing the
normalized fields together with the exact evidence text that produced them.

## Why This Matters

MOF and COF papers often contain synthesis information in dense experimental
paragraphs, supporting information, figure captions, and publisher-specific PDF
layouts. Researchers who want to compare materials across papers need to
recover names, routes, monomers, catalysts, solvents, temperatures, times,
atmospheres, interfaces, and substrates, but those details are usually not
available as a clean table.

Framework Miner provides a small open system for:

- Reproducing and preserving a DigiMOF-style MOF extraction workflow.
- Extending the same workflow toward COF synthesis chemistry.
- Building a curated benchmark from real open-access literature snippets.
- Producing local HTML reports that non-programmer readers can inspect.
- Keeping each extracted field tied to evidence text for human review.

This makes it useful as supporting infrastructure for review articles, database
curation, reproducible supplementary systems, and reader-facing literature
browsers in materials-science papers.

## Current Status

As of 2026-08-14:

- Benchmark cases: 69
- COF cases: 59
- MOF cases: 10
- Expected benchmark field values: 427
- Latest benchmark result: 69/69 cases passed, 427/427 expected fields recalled
- Latest test result: 94 passed, 1 warning

The remaining warning is a legacy ChemDataExtractor regex `FutureWarning`; it is
not a current functional failure.

This is an alpha research tool. It is useful for auditable extraction drafts and
benchmark-driven parser development. It should not yet be treated as a fully
automatic final database generator.

## What It Extracts

MOF extraction is based on the DigiMOF-style schema plus targeted heuristics:

- framework names, such as HKUST-1, ZIF-8, MIL-100 (Fe), MOF-808 variants
- synthesis routes, such as solvothermal, hydrothermal, mechanochemical,
  electrochemical, plasma-in-liquid
- topology and linker hints when available through the legacy parser

COF extraction is more synthesis-focused and currently targets:

- framework names and families
- polymerization or reaction routes
- linkages
- monomers and reagent-list precursors
- catalysts, acids, and bases
- solvents
- atmospheres and vacuum or carrier-gas conditions
- interfaces and substrates
- temperature and time

The parser is intentionally conservative: when a field cannot be supported by
the evidence text, it should be left blank rather than guessed.

## Repository Layout

```text
framework_miner/
  cli.py                 Command line extraction entry point
  cof.py                 COF synthesis heuristics
  legacy_digimof.py      DigiMOF-compatible MOF wrapper and shared parsing
  report.py              Local HTML review report renderer

benchmark/
  gold_cases.jsonl       Curated MOF/COF synthesis benchmark snippets

tests/
  test_*.py              Regression tests for parsers, benchmark, downloader, report

DigiMOF-database-master-main-main/
  ...                    Original DigiMOF code and vendored ChemDataExtractor fork

download_article_html.py DOI/URL downloader for local article snapshots
evaluate_framework_miner.py Benchmark evaluator
environment.yml          Conda environment
```

## Installation

The maintained environment is a Conda environment named `digimof-repro`.

```powershell
git clone https://github.com/hydrangeia/digimof-repro.git
cd digimof-repro
conda env create -f environment.yml
conda activate digimof-repro
```

If the environment already exists:

```powershell
conda env update -n digimof-repro -f environment.yml
```

Most commands below use `conda run` so they can be copied directly from a fresh
PowerShell session.

## Quick Start

Run both MOF and COF extraction on the small bundled examples and produce a
JSONL file plus a local HTML report:

```powershell
conda run --no-capture-output -n digimof-repro python -m framework_miner.cli sample_inputs -o sample_outputs\framework_miner_all_samples.jsonl --html-output sample_outputs\framework_miner_all_samples_report.html --framework all --framework-only
```

Open the generated report in a browser:

```text
sample_outputs\framework_miner_all_samples_report.html
```

The report is the recommended first interface for readers and collaborators. It
contains a searchable, filterable table of extracted records, normalized fields,
review labels, and evidence snippets.

## Extracting From A Local PDF

For a downloaded paper:

```powershell
conda run --no-capture-output -n digimof-repro python -m framework_miner.cli "path\to\paper.pdf" -o sample_outputs\paper.jsonl --html-output sample_outputs\paper_report.html --framework all --framework-only --pages 0 --max-chars 0 --no-merge
```

Useful options:

- `--framework mof`, `--framework cof`, or `--framework all`
- `--framework-only` keeps records that pass the selected framework filter
- `--pages 0` parses all PDF pages
- `--max-chars 0` disables the text cap
- `--no-merge` keeps paragraph-level records, which is best for review

Merged output is useful for a quick material-level overview. Paragraph-level
output is better for checking precision because it makes non-synthesis leakage
easier to spot.

## Downloading Articles By DOI Or URL

Create a UTF-8 text file with one DOI per line:

```text
10.1039/D1RA00942G
10.1002/anie.201811399
```

Download the target pages or PDFs:

```powershell
conda run --no-capture-output -n digimof-repro python download_article_html.py --doi-file dois.txt -o downloaded_articles
```

Then extract from the downloaded directory:

```powershell
conda run --no-capture-output -n digimof-repro python -m framework_miner.cli downloaded_articles -o sample_outputs\downloaded_articles.jsonl --html-output sample_outputs\downloaded_articles_report.html --framework all --framework-only --no-merge
```

DOI resolution depends on the publisher. Some DOI targets are open full text;
others are abstracts, paywalled pages, or PDFs. The downloader records the final
URL and saved local path in `downloaded_articles/manifest.jsonl`.

## Output Format

The JSONL output contains one extracted record per line. A simplified COF record
looks like this:

```json
{
  "schema_version": "framework_miner/0.2",
  "framework_type": "COF",
  "source": {
    "id": "paper.pdf",
    "kind": "pdf",
    "paragraph_index": 12
  },
  "fields": {
    "names": ["TFPT-COF"],
    "polymerization_routes": [{"route": "hydrazone formation"}],
    "monomers": [{"monomer": "TFPT", "role": "addition"}],
    "catalysts": [{"catalyst": "acetic acid"}],
    "solvents": [{"solvent": "mesitylene"}],
    "temperature": ["120 °C"],
    "time": ["72 h"]
  },
  "evidence_text": "Original paragraph text..."
}
```

The HTML report renders these records into a reviewable page and should be used
when sharing results with non-programmer collaborators.

## Benchmark And Tests

Run the curated benchmark:

```powershell
conda run --no-capture-output -n digimof-repro python evaluate_framework_miner.py
```

Run the full test suite:

```powershell
conda run --no-capture-output -n digimof-repro pytest tests -q -p no:cacheprovider --basetemp .pytest_tmp
```

The benchmark is a regression suite, not an unbiased accuracy estimate. It is
designed to keep real literature cases working as the parser evolves. Future
work should add more blind and negative cases, especially non-synthesis
characterization, application, review, and computational-reference paragraphs.

## Research Value

This project is valuable because it turns synthesis-text extraction into a
transparent and testable object:

- Every new rule is anchored by a real literature snippet.
- Each benchmark case states expected fields explicitly.
- HTML reports make mistakes visible to domain experts.
- The same interface can compare MOF and COF extraction behavior.
- The code records what is supported, what is still noisy, and where human
  review remains necessary.

For a paper, this can serve as a reader-facing companion system: readers can
inspect how synthesis fields were found, trace each field back to evidence, and
reuse the benchmark for future parser improvements.

## Limitations

- PDF text extraction can be noisy, especially for scanned files, equations,
  tables, captions, and supporting information.
- The parser is heuristic and high-precision oriented; it can miss valid fields
  when wording is unfamiliar.
- Full-paper scans can mix synthesis paragraphs with characterization,
  photocatalysis, stability testing, or workup conditions.
- Paywalled articles may not provide enough text for extraction.
- Current coverage is stronger for COF synthesis conditions than for the full
  range of MOF chemistry.

Always inspect the evidence text before using extracted records in scientific
claims.

## Relationship To DigiMOF

This repository preserves the original DigiMOF code under
`DigiMOF-database-master-main-main/` and builds a local wrapper around it for
modern reproducibility, local PDFs/HTML, benchmark evaluation, and COF-oriented
extensions.

The original DigiMOF code is not claimed as new work here. The new work is the
reproducible wrapper, benchmark harness, COF synthesis extractor, downloader,
HTML report interface, tests, and documentation.

## License

New code and documentation in this repository are released under the MIT License
unless otherwise noted.

Third-party components retain their original notices:

- Original DigiMOF code: MIT License, copyright 2020 Shu Huang.
- Vendored ChemDataExtractor fork: MIT License, copyright 2017 Matt Swain and
  contributors.

See `LICENSE` and `NOTICE.md` for details.

## Citation

If you use this repository in academic work, please cite the repository and the
underlying DigiMOF and ChemDataExtractor projects where relevant. A starter
`CITATION.cff` file is included and should be updated with a release DOI when a
formal archive is created.
