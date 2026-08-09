# Codex For OSS Application Notes

This file is a working note for describing the project in an OSS-support
application. It is not a benchmark result and should be updated before
submission.

## Short Project Description

Framework Miner is an auditable MOF/COF synthesis-literature extraction system.
It reproduces a DigiMOF-style MOF workflow, extends it toward COF synthesis
chemistry, and produces local HTML reports that show normalized fields beside
their source evidence. The project is intended to support open, reproducible
materials-science literature curation and future reader-facing supplementary
systems for research papers.

## Scientific Value

MOF and COF synthesis details are often buried in dense paragraphs, supporting
information, PDFs, and figure captions. Framework Miner makes those details
reviewable by extracting candidate fields and preserving evidence snippets. This
can reduce manual curation time, make paper-reading workflows reproducible, and
help readers inspect how synthesis records were derived.

## Current Evidence Of Maintenance

- Public GitHub repository: `https://github.com/hydrangeia/digimof-repro`
- Current benchmark: 69 real or curated synthesis cases
- Current validation: 69/69 benchmark cases passed, 427/427 expected fields
  recalled
- Current tests: 94 passed, 1 known legacy warning
- Continuous development has added real open-access COF and MOF cases over time
- The project includes a user-facing local HTML review report, not only raw JSONL

## How Codex/API Credits Would Help

Credits would be used for maintenance tasks that are difficult to do manually:

- Find and triage open-access MOF/COF synthesis papers.
- Add small, source-grounded benchmark cases.
- Improve extraction only when a real benchmark exposes a gap.
- Generate and review local HTML reports for user feedback.
- Add negative examples for non-synthesis paragraphs.
- Keep README, benchmark notes, and reproducibility docs synchronized.

The project already follows an accuracy-first loop: add one real case, preserve
UTF-8 text exactly, improve parser behavior narrowly, run benchmark and tests,
then commit verified changes.

## Honest Limitations

- The project is currently an alpha research tool, not a general production
  literature-mining service.
- Coverage is stronger for COF synthesis fields than for broad MOF extraction.
- The benchmark is a curated regression suite and does not yet measure unbiased
  real-world precision.
- Full-paper PDF extraction can still include non-synthesis leakage.

## Recommended Application Framing

Emphasize this as an open scientific infrastructure project:

- It helps make materials-literature curation more reproducible.
- It is useful to readers because every extracted field is evidence-linked.
- It supports future publication by serving as a transparent supplementary
  system.
- It has active maintenance history and measurable regression tests.
- It would benefit from Codex because the maintenance loop is exactly the kind of
  iterative, evidence-checking software work where AI assistance is helpful.

