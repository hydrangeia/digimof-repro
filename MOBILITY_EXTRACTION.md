# Mobility Miner: Evidence Contract and Roadmap

`mobility_miner` is an experimental sibling to the MOF/COF synthesis
extractors. It locates charge-carrier mobility claims in local PDFs, HTML/XML,
plain text, and URLs, then keeps each normalized value attached to the exact
source block and character span that produced it.

It is a curation aid, not a source of scientific authority. A record must still
be checked against the paper before it is used as a label or manuscript claim.

## What the first version extracts

- mobility scalars, ranges, inequalities, uncertainty, and original unit text;
- normalized values in `cm^2 V^-1 s^-1`, including conversion from
  `m^2 V^-1 s^-1`;
- electron, hole, ambipolar, ion, or proton carrier context when explicit;
  carrier evidence keeps an exact span, while multi-carrier claims require
  clause separation, unambiguous nearest-value linkage, or explicit
  `respectively` alignment and otherwise receive a review flag;
- temperature and crystallographic/in-plane direction when explicit;
- temperature is assigned only from the value's own contrast/semicolon clause;
  multiple temperatures in one clause remain unaligned and receive a review flag;
- crystallographic direction follows the same clause-local alignment rule;
  multiple distinct directions in one clause remain unassigned for review;
- experimental methods such as FET/OFET, Hall, SCLC, TOF, TRMC, THz, and
  photo-CELIV, including OPTP/TRTS aliases; explicit methods are bound within
  each value's contrast/semicolon clause and retain exact evidence spans;
- computational algorithms such as deformation-potential theory, BTE,
  Kubo-Greenwood, Marcus theory, transient localization, kinetic Monte Carlo,
  Frohlich-polaron, and Osaka models, with the same clause-local binding rule;
- experimental analysis models such as Drude and Drude-Smith, kept separate
  from computational mobility algorithms and linked to their exact spans;
- explicit distinction between direct mobility and an effective `phi * mu`
  mobility-yield product, including a same-sentence lower-bound relation and
  exact qualifier spans;
- per-value FET `saturation` or `linear` regime when it is explicit in the same
  sentence, with an exact regime span;
- `experimental`, `computational`, `reported_unspecified`, or `unspecified`
  determination;
- `current_work`, `prior_work`, `mixed_or_ambiguous`, or `unspecified` source
  relation, with exact provenance-cue spans;
- citation markers visible in the evidence block, plus HTML DOI/title metadata;
- DOI provenance inferred conservatively from DOI-organized local PDF filenames,
  with `doi_source: filename_inference` so it cannot be mistaken for embedded
  publisher metadata;
- explicit review flags instead of guessed material, method, or provenance.

The parser retains method/algorithm-only candidate paragraphs even when no
quantity is found. Use `--values-only` when only normalized numeric records are
wanted.

For PDFs, `pdfplumber` is preferred because it preserves superscripts and unit
order more reliably than the legacy `pdfminer` path. Evidence is narrowed to
sentence-scale passages before extraction so a method mentioned at the top of a
two-column page is not silently attached to an unrelated value below it. The
legacy parser remains a fallback. Image-only or outlined-text PDFs still need an
OCR stage; the parser does not invent text when a usable text layer is absent.

## Command line

```powershell
conda run --no-capture-output -n digimof-repro python -m mobility_miner.cli papers -o sample_outputs\mobility.jsonl --html-output sample_outputs\mobility_report.html --values-only
```

For all pages of a PDF, keep the default `--pages 0`. A URL can be supplied in
place of a local path. The output remains paragraph- or table-row-level by
default because merging before review can silently attach a method from one
claim to a value from another.

## Record shape

```json
{
  "schema_version": "mobility_miner/0.1",
  "record_type": "charge_carrier_mobility",
  "source": {
    "id": "paper.html",
    "kind": "url_html",
    "document_title": "Example title",
    "doi": "10.xxxx/example",
    "block_index": 42,
    "element_type": "p"
  },
  "fields": {
    "materials": [{
      "material": "monolayer MoS2",
      "raw_text": "monolayer MoS2",
      "span": {"start": 56, "end": 70}
    }],
    "mobilities": [{
      "raw_value": "2.4 x 10^3",
      "raw_units": "cm^2 V^-1 s^-1",
      "value": 2400.0,
      "standard_units": "cm^2 V^-1 s^-1",
      "carrier": "electron",
      "determination": "computational",
      "source_relation": "current_work",
      "material_refs": [0],
      "algorithms": ["deformation-potential theory"],
      "span": {"start": 126, "end": 153, "text": "2.4 x 10^3 cm^2 V^-1 s^-1"}
    }]
  },
  "evidence_text": "Original paragraph or table row...",
  "passes_mobility_filter": true,
  "extraction_method": "mobility_evidence_heuristic"
}
```

`source_relation` is deliberately separate from `determination`: a cited prior
work can itself contain either a measured or a calculated value. A citation
marker is not resolved into a bibliography entry yet; `prior_work` without full
bibliographic identity must remain a review item.

`material_refs` is emitted only when a passage has exactly one conservative
material candidate. Multiple materials are not assigned by proximity; the
measurement instead retains `multiple_materials_unaligned`. This is a narrow
linkage guarantee, not a document-level entity resolver.

For effective quantities the measurement can also contain:

```json
{
  "quantity_kind": "mobility_yield_product",
  "quantity_label": {
    "raw_text": "effective mobility",
    "span": {"start": 20, "end": 38}
  },
  "mobility_relation": {
    "relation": "lower_bound_of_true_mobility",
    "raw_text": "lower bound for mu",
    "span": {"start": 76, "end": 94}
  },
  "review_flags": ["reported_quantity_is_not_direct_mobility"]
}
```

## Linked-record target and current gap audit

The eventual `mobility_miner/0.2` contract should separate document entities
instead of copying every nearby phrase onto every value:

```text
materials[] -> synthesis_batches[] -> samples[] -> devices[]
     |                                      |
     +----------------> measurements[] <----+
                              |
                         evidence_refs[]
```

Each entity needs a stable local ID plus exact evidence references. A
measurement should link to one or more material IDs and, where applicable, one
sample, device, synthesis batch, method, or computational model. Conditions and
assumptions belong on the measurement only when their evidence scope supports
that link. Unresolved links must stay empty and carry a review flag.

Current coverage is intentionally narrower:

- **Covered:** mobility value/range/uncertainty, original and normalized unit,
  basic carrier, temperature/direction, experimental method, computational
  algorithm, analysis model, evidence text/span, page/paragraph, DOI, and a
  conservative current/prior heuristic.
- **Newly linked:** exact material spans and `material_refs` for a unique
  same-passage material; direct mobility versus explicit effective `phi * mu`
  product and lower-bound semantics.
- **Partial:** material identity, determination, and source relation. These are
  passage heuristics and do not yet resolve cross-page evidence or references.
- **Blocked:** structure/phase/topology/space group, synthesis and processing,
  sample/device state, thickness/morphology/substrate/electrodes, bias/field,
  carrier density/doping, atmosphere/illumination/frequency, computational
  assumptions, table/figure cell coordinates, and safe cross-paragraph entity
  linkage.

The blocked fields are not filled from document-level co-occurrence. That rule
prevents a condition from one composition, temperature, method, or cited prior
work being silently attached to another mobility value.

## ChemDataExtractor 2 decision

ChemDataExtractor 2 is promising for the next layer. Its official project lists
property grammars, table parsing, interdependency resolution, and chemistry-aware
NER, and its `QuantityModel`/custom-dimension system can represent mobility as
the composite dimension `Length^2 / (Voltage * Time)` with automatic unit
conversion.

It should not be installed into `digimof-repro` directly:

- this repository's reproducibility environment uses Python 3.8 and a modified
  ChemDataExtractor 1.x tree;
- the current CDE2 repository states Python 3.9-3.11 support;
- both implementations import as `chemdataextractor`, so putting them in one
  environment would make parser selection depend on import-path order.

The safe integration is a separate Python 3.11 environment or subprocess that
serializes CDE2 results into the `mobility_miner/0.1` record contract. That
adapter should be evaluated only after a mobility benchmark exists; otherwise
extra model complexity can hide alignment errors instead of improving them.

Official references:

- <https://github.com/CambridgeMolecularEngineering/chemdataextractor2>
- <https://cambridgemolecularengineering-chemdataextractor-development.readthedocs-hosted.com/en/latest/examples/creating_units.html>
- <https://cambridgemolecularengineering-chemdataextractor-development.readthedocs-hosted.com/en/latest/code_documentation.html>

## Recommended next benchmark slices

1. Original experimental claims: FET, Hall, SCLC, TOF, TRMC/THz.
2. Original computational claims: DP, BTE, Marcus/hopping, transient
   localization, Frohlich/Osaka.
3. Tables with shared units and electron/hole columns.
4. Review or introduction paragraphs quoting prior work.
5. Negative cases: conductivity, diffusion coefficient, recombination lifetime,
   mobility mentioned without a value, and citation lists.
6. Ambiguous cases: multiple materials, values, temperatures, directions, or
   methods in the same sentence.

Precision, value-to-material alignment, method attribution, and citation-source
resolution should be scored separately. A single field-recall score would hide
the errors most likely to contaminate a mobility database.

## Optional real-corpus checks

`tests/fixtures/mobility_gold_cases.json` records one evidence-scoped case for
each of COF, MOF, organic small-molecule semiconductor (OSM), and perovskite
(PVSK). It stores normalized facts and explicit `must_not_link` constraints,
not article text. Cases remain `BLOCKED` or `PARTIAL_PASS` until material,
sample, condition, and value linkage is independently supported.

`tests/test_mobility_real_corpus.py` exercises DOI-addressed pages from
`D:/papers/data` without copying article text into the repository. It covers a
UiO-66 deformation-potential result, a perovskite OPTP range with uncertainty,
a COF TRTS mobility-yield product, and OSM single-crystal FET values. The tests
skip cleanly when the private corpus or `pdfplumber` is unavailable.

```powershell
python tests\test_mobility_real_corpus.py
```
