# Notices

This repository combines new Framework Miner code with preserved third-party
MIT-licensed components.

## New Project Code

Unless otherwise noted, the wrapper code, COF extraction heuristics, benchmark
harness, downloader, HTML report generator, tests, and documentation in the
repository root, `framework_miner/`, `benchmark/`, and `tests/` are released
under the repository-level MIT License.

Copyright (c) 2026 DigiMOF Reproduction and Framework Miner contributors.

## Original DigiMOF Code

The directory `DigiMOF-database-master-main-main/` contains code from the
DigiMOF database project.

License: MIT License

Copyright (c) 2020 Shu Huang

The original license text is preserved at:

```text
DigiMOF-database-master-main-main/LICENSE
```

## Vendored ChemDataExtractor Fork

The directory
`DigiMOF-database-master-main-main/chemdataextractor_MOFs/chemdataextractor/`
contains a vendored ChemDataExtractor fork used by the original DigiMOF stack.

License: MIT License

Copyright 2017 Matt Swain and contributors

The original license text is preserved at:

```text
DigiMOF-database-master-main-main/chemdataextractor_MOFs/chemdataextractor/LICENSE
```

## Article Text, PDFs, And Downloaded Data

Downloaded articles, raw article text, local PDFs, generated extraction outputs,
and local ChemDataExtractor data are not intended to be committed to this
repository unless their redistribution rights have been checked separately.

Relevant ignored paths include:

```text
cde-data/
downloaded_articles/
downloaded_articles_*.txt
sample_outputs/*
*.pdf
```

## Scientific Use

Extraction output should be treated as an auditable draft. Users should inspect
the evidence snippets before relying on extracted values in scientific claims.

