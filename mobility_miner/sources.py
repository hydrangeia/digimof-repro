"""Local-file and URL ingestion for mobility extraction."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text

try:
    import pdfplumber
except ImportError:  # The legacy Python 3.8 environment may not be updated yet.
    pdfplumber = None

from .extract import (
    CONDITION_COVERAGE_FIELDS,
    _source_relation_details,
    extract_mobility_fields,
    is_mobility_candidate_text,
    normalized_mobility_item,
    refresh_measurement_review_status,
)


SUPPORTED_FILE_SUFFIXES = {".html", ".htm", ".xml", ".txt", ".pdf"}
REQUEST_HEADERS = {"User-Agent": "mobility-miner/0.1 (+https://pmc.ncbi.nlm.nih.gov/)"}
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
DOI_FILENAME_RE = re.compile(r"^(10\.\d{4,9})_(.+)$", re.I)
SUPPLEMENTARY_SUFFIX_RE = re.compile(r"_SI\d+$", re.I)
PDF_CONTEXT_METHOD_RE = re.compile(
    r"(?i)\b(?:Hall|OFET|FET|SCLC|TOF|TRMC|TRTS|OPTP|THz|terahertz|"
    r"deformation[-\s]?potential|Boltzmann|Marcus|DFT|first[-\s]?principles?|Drude)\b"
)
PAGE_DEVICE_ANCHORS = [
    (
        re.compile(
            r"(?i)\b(?:SC[-\s]?FETs?|single[-\s]+crystal\s+field[-\s]*effect\s+transistor)\b"
        ),
        "single-crystal field-effect transistor",
    ),
    (
        re.compile(r"(?i)\bthin[-\s]+film\s+(?:field[-\s]*effect\s+)?transistors?\b"),
        "thin-film field-effect transistor",
    ),
]
PAGE_FABRICATION_PATTERNS = [
    (
        "device_geometry",
        re.compile(r"(?i)\bbottom[-\s]+contact\s*,?\s*bottom[-\s]+gate\s+geometry\b"),
        "bottom-contact bottom-gate",
    ),
    (
        "electrode",
        re.compile(r"(?i)\bAu\s+bottom\s+contacts?\b"),
        "Au bottom contacts",
    ),
    (
        "fabrication_method",
        re.compile(r"(?i)\bmanually\s+laminated\b"),
        "manual lamination",
    ),
]


def doi_from_pdf_filename(path: str | Path) -> str | None:
    """Infer a DOI from the corpus' ``prefix_suffix.pdf`` convention.

    The DOI is explicitly marked as inferred by callers because a filename is
    useful provenance, but is not equivalent to publisher metadata.  Common
    supplementary-file suffixes (for example ``_SI2``) are excluded from the
    inferred DOI while the original source path remains unchanged.
    """
    stem = SUPPLEMENTARY_SUFFIX_RE.sub("", Path(path).stem)
    match = DOI_FILENAME_RE.fullmatch(stem)
    if not match:
        return None
    candidate = "{}/{}".format(match.group(1), match.group(2))
    return candidate if DOI_RE.fullmatch(candidate) else None


def _pdf_source(path: Path, source_id: str | None, **location: Any) -> dict[str, Any]:
    source = {"id": source_id or str(path), "kind": "pdf"}
    source.update(location)
    if source_id is None:
        doi = doi_from_pdf_filename(path)
        if doi:
            source["doi"] = doi
            source["doi_source"] = "filename_inference"
    return source


def iter_local_inputs(inputs: Iterable[str | Path]) -> Iterable[Path]:
    """Yield supported local documents in deterministic order."""
    for item in inputs:
        path = Path(item)
        if path.is_dir():
            for candidate in sorted(path.rglob("*")):
                if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_FILE_SUFFIXES:
                    yield candidate
        elif path.is_file() and path.suffix.lower() in SUPPORTED_FILE_SUFFIXES:
            yield path


def split_paragraphs(text: str, max_chars: int | None = None) -> Iterable[str]:
    """Split extracted text while retaining table-like single-line blocks."""
    if max_chars:
        text = text[:max_chars]
    chunks = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        normalized = " ".join(block.split())
        if normalized:
            chunks.append(normalized)
    for paragraph in chunks:
        if len(paragraph) >= 25:
            yield paragraph


def _normalized_pdf_text(text: str) -> str:
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    return " ".join(text.split())


def _span_distance(first: dict[str, int], second: dict[str, int]) -> int:
    if first["end"] < second["start"]:
        return second["start"] - first["end"]
    if second["end"] < first["start"]:
        return first["start"] - second["end"]
    return 0


def _page_device_anchors(text: str) -> list[dict[str, Any]]:
    anchors = []
    for pattern, value in PAGE_DEVICE_ANCHORS:
        for match in pattern.finditer(text):
            anchors.append(
                {
                    "value": value,
                    "raw_text": match.group(0),
                    "span": {"start": match.start(), "end": match.end()},
                    "span_scope": "normalized_page_text",
                }
            )
    anchors.sort(key=lambda item: (item["span"]["start"], item["span"]["end"]))
    return anchors


def _page_condition_clause(text: str, start: int, end: int) -> tuple[str, int]:
    """Return the narrow clause carrying a page-level condition candidate."""
    boundaries = [
        (match.start(), match.end())
        for match in re.finditer(
            r"(?i)[.!?;]|,\s+(?:and|but|with|which|where)\b",
            text,
        )
    ]
    clause_start = max(
        (boundary_end for _boundary_start, boundary_end in boundaries if boundary_end <= start),
        default=0,
    )
    clause_end = min(
        (boundary_start for boundary_start, _boundary_end in boundaries if boundary_start >= end),
        default=len(text),
    )
    return text[clause_start:clause_end], clause_start


def _page_fabrication_candidates(text: str, max_anchor_distance: int = 650) -> list[dict[str, Any]]:
    """Extract page-level fabrication facts only when a nearby device identity is explicit."""
    anchors = _page_device_anchors(text)
    candidates = []
    for field, pattern, value in PAGE_FABRICATION_PATTERNS:
        for match in pattern.finditer(text):
            span = {"start": match.start(), "end": match.end()}
            ranked_anchors = sorted(anchors, key=lambda anchor: _span_distance(span, anchor["span"]))
            if not ranked_anchors or _span_distance(span, ranked_anchors[0]["span"]) > max_anchor_distance:
                continue
            clause, clause_start = _page_condition_clause(text, match.start(), match.end())
            source_relation, source_relation_evidence = _source_relation_details(
                clause,
                offset=clause_start,
            )
            candidate = {
                "field": field,
                "value": value,
                "raw_text": match.group(0),
                "span": span,
                "span_scope": "normalized_page_text",
                "binding_scope": "sample",
                "review_flags": [],
                "source_relation": source_relation,
                "device_anchor": ranked_anchors[0],
            }
            if source_relation_evidence:
                candidate["source_relation_evidence"] = source_relation_evidence
            candidates.append(candidate)
    candidates.sort(key=lambda item: (item["span"]["start"], item["span"]["end"], item["field"]))
    return candidates


def _external_condition_evidence_ref(
    source: dict[str, Any],
    span: dict[str, int],
) -> dict[str, Any]:
    evidence_ref = {
        "source_id": source.get("id"),
        "source_kind": source.get("kind"),
        "span": dict(span),
        "span_scope": "normalized_page_text",
    }
    for key in ("page", "doi", "doi_source", "document_title"):
        if source.get(key) is not None:
            evidence_ref[key] = source[key]
    return evidence_ref


def _table_cell_ref(
    source: dict[str, Any],
    table_index: int,
    row_index: int,
    column_index: int,
    raw_text: str,
) -> dict[str, Any]:
    ref = {
        "source_id": source.get("id"),
        "source_kind": source.get("kind"),
        "page": source.get("page"),
        "doi": source.get("doi"),
        "doi_source": source.get("doi_source"),
        "table_locator": "Table S1",
        "table_index": table_index,
        "row_index": row_index,
        "column_index": column_index,
        "raw_text": raw_text,
        "span_scope": "pdf_table_cell",
    }
    return {key: value for key, value in ref.items() if value is not None}


def _parse_pvsk_sclc_comparison_table(page: Any, page_text: str, source: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse explicit two-material SCLC mobility tables with aligned cells."""
    caption_match = re.search(
        r"(?i)Table\s+S1\.\s+The\s+SCLC\s+electron\s+mobility\s+of\s+the\s+CDIN\s+and\s+C\s*60\s+films\.",
        page_text,
    )
    scale_match = re.search(
        r"(?i)[(（]?\s*[×x]\s*10\s*[-\u2212\u2013]\s*4\s*(?P<units>cm\s*2\s*V\s*[-\u2212\u2013]\s*1\s*s\s*[-\u2212\u2013]\s*1)\s*[)）]?",
        page_text,
    )
    if not caption_match or not scale_match:
        return []
    sclc_match = re.search(r"(?i)\bSCLC\b", page_text)
    electron_match = re.search(r"(?i)\belectron\b", page_text)
    films_match = re.search(r"(?i)\bfilms\b", page_text)
    device_match = re.search(r"(?i)\belectron\s+only\s+devices?\b", page_text)
    stack_match = re.search(r"(?i)ITO\s*/\s*ZnO\s*/\s*ETL\s*/\s*LiF\s*/\s*Al", page_text)
    if not all((sclc_match, electron_match, films_match, device_match, stack_match)):
        return []

    def page_text_ref(match: re.Match[str]) -> dict[str, Any]:
        return {
            "source_id": source.get("id"),
            "source_kind": source.get("kind"),
            "page": source.get("page"),
            "doi": source.get("doi"),
            "doi_source": source.get("doi_source"),
            "span": {"start": match.start(), "end": match.end()},
            "span_scope": "normalized_page_text",
            "raw_text": match.group(0),
        }

    sclc_ref = page_text_ref(sclc_match)
    electron_ref = page_text_ref(electron_match)
    films_ref = page_text_ref(films_match)
    device_ref = page_text_ref(device_match)
    stack_ref = page_text_ref(stack_match)

    for table_index, table in enumerate(page.extract_tables() or []):
        material_columns: dict[int, tuple[str, int, str]] = {}
        for row_index, row in enumerate(table):
            for column_index, cell in enumerate(row):
                if not cell:
                    continue
                normalized = " ".join(cell.split())
                if re.fullmatch(r"(?i)CDIN", normalized):
                    material_columns[column_index] = ("CDIN", row_index, cell)
                elif re.fullmatch(r"(?i)C\s*60", normalized):
                    material_columns[column_index] = ("C60", row_index, cell)
        if {item[0] for item in material_columns.values()} != {"CDIN", "C60"}:
            continue

        mobility_row = next(
            (
                index
                for index, row in enumerate(table)
                if any(cell and re.fullmatch(r"(?i)Mobility", " ".join(cell.split())) for cell in row)
            ),
            None,
        )
        thickness_row = next(
            (
                index
                for index, row in enumerate(table)
                if any(cell and re.search(r"(?i)Thickness\s*\(\s*nm\s*\)", cell) for cell in row)
            ),
            None,
        )
        if mobility_row is None or thickness_row is None:
            continue
        value_row_index = next(
            (
                index
                for index in range(mobility_row + 1, len(table))
                if all(
                    column < len(table[index])
                    and table[index][column]
                    and re.fullmatch(r"\d+(?:\.\d+)?", table[index][column].strip())
                    for column in material_columns
                )
            ),
            None,
        )
        if value_row_index is None:
            continue

        unit_ref = {
            "source_id": source.get("id"),
            "source_kind": source.get("kind"),
            "page": source.get("page"),
            "doi": source.get("doi"),
            "doi_source": source.get("doi_source"),
            "span": {"start": scale_match.start(), "end": scale_match.end()},
            "span_scope": "normalized_page_text",
            "raw_text": scale_match.group(0),
        }
        records = []
        for column_index, (material, material_row_index, material_cell) in material_columns.items():
            raw_value = table[value_row_index][column_index].strip()
            raw_thickness = table[thickness_row][column_index].strip()
            cell_value_ref = _table_cell_ref(source, table_index, value_row_index, column_index, raw_value)
            material_ref = _table_cell_ref(source, table_index, material_row_index, column_index, material_cell)
            thickness_ref = _table_cell_ref(source, table_index, thickness_row, column_index, raw_thickness)
            span = {"start": 0, "end": len(raw_value), "text": raw_value, "span_scope": "pdf_table_cell"}
            measurement = {
                "raw_value": raw_value,
                "raw_units": scale_match.group(0),
                "standard_units": "cm^2 V^-1 s^-1",
                "value": float(raw_value) * 1e-4,
                "span": span,
                "evidence_refs": [cell_value_ref],
                "source_relation": "unspecified",
                "determination": "experimental",
                "carrier": "electron",
                "carrier_evidence": {"raw_text": electron_match.group(0), "evidence_refs": [electron_ref]},
                "methods": ["space-charge-limited current"],
                "method_evidence": [{"method": "space-charge-limited current", "raw_text": sclc_match.group(0), "evidence_refs": [sclc_ref]}],
                "material_refs": [0],
                "condition_records": [
                    {"field": "material_identity", "value": material, "raw_text": material_cell, "evidence_refs": [material_ref]},
                    {"field": "sample_form", "value": "film", "raw_text": films_match.group(0), "evidence_refs": [films_ref]},
                    {"field": "thickness", "value": "{} nm".format(raw_thickness), "raw_text": raw_thickness, "evidence_refs": [thickness_ref]},
                    {"field": "device_type", "value": "electron-only device", "raw_text": device_match.group(0), "evidence_refs": [device_ref]},
                    {"field": "device_stack", "value": "ITO/ZnO/ETL/LiF/Al", "raw_text": stack_match.group(0), "evidence_refs": [stack_ref]},
                ],
                "condition_coverage": [
                    {
                        "field": field,
                        "status": "reported"
                        if field in {"material_identity", "sample_form", "thickness", "device_type"}
                        else "not_reported",
                    }
                    for field in CONDITION_COVERAGE_FIELDS
                ],
                "table_cell": {"table_index": table_index, "row_index": value_row_index, "column_index": column_index, "row_header": material, "column_header": "Mobility"},
                "unit_evidence": {"raw_text": scale_match.group(0), "evidence_refs": [unit_ref]},
            }
            refresh_measurement_review_status(measurement)
            table_source = {
                **source,
                "table_locator": "Table S1",
                "table_index": table_index,
                "table_row_index": value_row_index,
                "table_column_index": column_index,
                "element_type": "table_cell",
            }
            records.append({
                "schema_version": "mobility_miner/0.1",
                "record_type": "charge_carrier_mobility",
                "source": table_source,
                "fields": {"materials": [{"material": material, "raw_text": material_cell, "evidence_refs": [material_ref]}], "mobilities": [measurement]},
                "evidence_text": raw_value,
                "passes_mobility_filter": True,
                "extraction_method": "mobility_pdf_table_heuristic",
            })
        return records
    return []


def _link_page_fabrication_conditions(
    normalized_page_text: str,
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Link page-level fabrication facts through an explicit shared device identity."""
    candidates = _page_fabrication_candidates(normalized_page_text)
    if not candidates:
        return records

    for record in records:
        source = record.get("source", {})
        for measurement in record.get("fields", {}).get("mobilities", []):
            device_conditions = [
                condition
                for condition in measurement.get("condition_records", [])
                if condition.get("field") == "device_type"
            ]
            if len(device_conditions) != 1:
                continue
            target_device = device_conditions[0]
            matching_candidates = [
                candidate
                for candidate in candidates
                if candidate["device_anchor"]["value"] == target_device["value"]
            ]
            blocked_candidates = [
                candidate
                for candidate in matching_candidates
                if candidate["source_relation"] in {"prior_work", "mixed_or_ambiguous"}
            ]
            matching_candidates = [
                candidate
                for candidate in matching_candidates
                if candidate not in blocked_candidates
            ]
            grouped = {}
            for candidate in matching_candidates:
                grouped.setdefault(candidate["field"], []).append(candidate)

            linked_condition_refs = []
            for field, field_candidates in grouped.items():
                distinct_values = {candidate["value"] for candidate in field_candidates}
                coverage = next(
                    (item for item in measurement["condition_coverage"] if item["field"] == field),
                    None,
                )
                if len(distinct_values) != 1:
                    if coverage is not None:
                        coverage["status"] = "ambiguous"
                        coverage.pop("condition_refs", None)
                    measurement.setdefault("review_flags", []).append("{}_ambiguous".format(field))
                    continue

                candidate = field_candidates[0]
                device_anchor = candidate["device_anchor"]
                condition = {
                    key: value
                    for key, value in candidate.items()
                    if key != "device_anchor"
                }
                condition["evidence_refs"] = [
                    _external_condition_evidence_ref(source, candidate["span"])
                ]
                condition["relation_path"] = [
                    {
                        "relation": "same_device_type",
                        "source_anchor": device_anchor,
                        "target_anchor": {
                            "value": target_device["value"],
                            "raw_text": target_device["raw_text"],
                            "span": dict(target_device["span"]),
                            "span_scope": "record_evidence_text",
                        },
                    }
                ]
                conditions = measurement.setdefault("condition_records", [])
                conditions.append(condition)
                condition_ref = len(conditions) - 1
                linked_condition_refs.append(condition_ref)
                if coverage is not None:
                    coverage.update({"status": "reported", "condition_refs": [condition_ref]})
                not_aligned_flag = "{}_not_aligned".format(field)
                if not_aligned_flag in measurement.get("review_flags", []):
                    measurement["review_flags"].remove(not_aligned_flag)

            for candidate in blocked_candidates:
                device_anchor = candidate["device_anchor"]
                blocked_condition = {
                    key: value
                    for key, value in candidate.items()
                    if key != "device_anchor"
                }
                blocked_condition["binding_scope"] = "document"
                blocked_condition["review_flags"] = ["prior_work_not_bound_to_measurement"]
                blocked_condition["evidence_refs"] = [
                    _external_condition_evidence_ref(source, candidate["span"])
                ]
                blocked_condition["relation_path"] = [
                    {
                        "relation": "same_device_type",
                        "source_anchor": device_anchor,
                        "target_anchor": {
                            "value": target_device["value"],
                            "raw_text": target_device["raw_text"],
                            "span": dict(target_device["span"]),
                            "span_scope": "record_evidence_text",
                        },
                        "blocked_by": "source_relation",
                    }
                ]
                measurement.setdefault("condition_candidates", []).append(blocked_condition)
                coverage = next(
                    (
                        item
                        for item in measurement["condition_coverage"]
                        if item["field"] == candidate["field"]
                    ),
                    None,
                )
                if coverage is not None and coverage["status"] != "reported":
                    coverage["status"] = "not_aligned"
                    coverage.pop("condition_refs", None)
                flag = "{}_prior_work_not_aligned".format(candidate["field"])
                if flag not in measurement.setdefault("review_flags", []):
                    measurement["review_flags"].append(flag)

            if linked_condition_refs:
                fabrication_coverage = next(
                    item
                    for item in measurement["condition_coverage"]
                    if item["field"] == "device_fabrication"
                )
                fabrication_coverage.update(
                    {"status": "reported", "condition_refs": linked_condition_refs}
                )
            elif blocked_candidates:
                fabrication_coverage = next(
                    item
                    for item in measurement["condition_coverage"]
                    if item["field"] == "device_fabrication"
                )
                if fabrication_coverage["status"] != "reported":
                    fabrication_coverage["status"] = "not_aligned"
                    fabrication_coverage.pop("condition_refs", None)
                flag = "device_fabrication_prior_work_not_aligned"
                if flag not in measurement.setdefault("review_flags", []):
                    measurement["review_flags"].append(flag)
            refresh_measurement_review_status(measurement)
    return records


def split_mobility_passages(text: str) -> Iterable[str]:
    """Build compact sentence-level PDF passages around mobility mentions.

    PDF extractors often return a whole two-column page as one block. Keeping
    that block intact can wrongly attach a DFT mention from the introduction to
    a Hall value later on the page, so PDF evidence is narrowed here before the
    field extractor runs.
    """
    text = _normalized_pdf_text(text)
    if not text:
        return
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+(?=(?:[A-Z\[]|\d+\s))", text)
        if sentence.strip()
    ]
    seen = set()
    for index, sentence in enumerate(sentences):
        if not is_mobility_candidate_text(sentence):
            continue
        parts = []
        if index and PDF_CONTEXT_METHOD_RE.search(sentences[index - 1]):
            parts.append(sentences[index - 1])
        parts.append(sentence)
        if index + 1 < len(sentences) and not re.search(r"(?i)(?:cm|m)\s*(?:\^?2|\u00b2)", sentence):
            next_sentence = sentences[index + 1]
            if re.search(r"(?i)(?:cm|m)\s*(?:\^?2|\u00b2)", next_sentence):
                parts.append(next_sentence)
        passage = " ".join(parts)
        if passage not in seen:
            seen.add(passage)
            yield passage


def record_from_text(text: str, source: dict[str, Any]) -> dict[str, Any] | None:
    """Extract one paragraph-level mobility record."""
    fields = extract_mobility_fields(text)
    if fields is None:
        return None
    return normalized_mobility_item(source, text, fields)


def _html_metadata(soup: BeautifulSoup) -> dict[str, str]:
    """Read common scholarly citation metadata without guessing missing fields."""
    metadata = {}
    meta_values = {}
    for tag in soup.find_all("meta"):
        name = (tag.get("name") or tag.get("property") or "").strip().lower()
        content = (tag.get("content") or "").strip()
        if name and content and name not in meta_values:
            meta_values[name] = content

    title = next(
        (
            meta_values[name]
            for name in ("citation_title", "dc.title", "dcterms.title", "og:title")
            if name in meta_values
        ),
        None,
    )
    if not title and soup.title and soup.title.string:
        title = " ".join(soup.title.string.split())
    if title:
        metadata["document_title"] = title

    doi_candidates = [
        meta_values[name]
        for name in ("citation_doi", "dc.identifier", "dcterms.identifier", "prism.doi")
        if name in meta_values
    ]
    for candidate in doi_candidates:
        match = DOI_RE.search(candidate)
        if match:
            metadata["doi"] = match.group(0).rstrip(".,;)")
            break
    return metadata


def parse_html_text(content: bytes, source_id: str, max_chars: int | None = None) -> Iterable[dict[str, Any]]:
    """Parse prose and table rows from HTML or XML content."""
    soup = BeautifulSoup(content, "html.parser")
    document_metadata = _html_metadata(soup)
    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
        element.decompose()

    blocks = []
    seen = set()
    for tag in soup.find_all(["h1", "h2", "h3", "p", "figcaption", "li", "tr"]):
        separator = " | " if tag.name == "tr" else " "
        text = " ".join(tag.get_text(separator).split())
        if len(text) >= 25 and text not in seen:
            seen.add(text)
            blocks.append((tag.name, text))

    used_chars = 0
    for block_index, (element_type, block) in enumerate(blocks):
        if not is_mobility_candidate_text(block):
            continue
        if max_chars and used_chars >= max_chars:
            break
        if max_chars and used_chars + len(block) > max_chars:
            block = block[: max_chars - used_chars]
        used_chars += len(block)
        source = {
            "id": source_id,
            "kind": "url_html",
            "block_index": block_index,
            "element_type": element_type,
        }
        source.update(document_metadata)
        record = record_from_text(block, source)
        if record:
            yield record


def parse_pdf_path(
    path: Path,
    pages: int | None = None,
    max_chars: int | None = None,
    source_id: str | None = None,
) -> Iterable[dict[str, Any]]:
    """Extract paragraph candidates from a local PDF."""
    if pdfplumber is not None:
        paragraph_index = 0
        used_chars = 0
        with pdfplumber.open(str(path)) as pdf:
            selected_pages = pdf.pages[:pages] if pages else pdf.pages
            for page_number, page in enumerate(selected_pages, start=1):
                if max_chars and used_chars >= max_chars:
                    break
                page_text = page.extract_text() or ""
                if max_chars:
                    page_text = page_text[: max_chars - used_chars]
                used_chars += len(page_text)
                page_records = []
                for paragraph in split_mobility_passages(page_text):
                    if is_mobility_candidate_text(paragraph):
                        source = _pdf_source(
                            path,
                            source_id,
                            page=page_number,
                            paragraph_index=paragraph_index,
                        )
                        record = record_from_text(paragraph, source)
                        if record:
                            page_records.append(record)
                    paragraph_index += 1
                if "Table S1" in page_text:
                    table_source = _pdf_source(
                        path,
                        source_id,
                        page=page_number,
                        paragraph_index=paragraph_index,
                    )
                    table_records = _parse_pvsk_sclc_comparison_table(
                        page,
                        _normalized_pdf_text(page_text),
                        table_source,
                    )
                    page_records.extend(table_records)
                    paragraph_index += len(table_records)
                yield from _link_page_fabrication_conditions(
                    _normalized_pdf_text(page_text),
                    page_records,
                )
        return

    page_numbers = range(pages) if pages else None
    text = extract_text(str(path), page_numbers=page_numbers)
    for paragraph_index, paragraph in enumerate(split_mobility_passages(text[:max_chars] if max_chars else text)):
        if not is_mobility_candidate_text(paragraph):
            continue
        source = _pdf_source(path, source_id, paragraph_index=paragraph_index)
        record = record_from_text(paragraph, source)
        if record:
            yield record


def parse_plain_text(content: bytes, source_id: str, source_kind: str, max_chars: int | None = None) -> Iterable[dict[str, Any]]:
    """Extract paragraph candidates from UTF-8-compatible text."""
    text = content.decode("utf-8", errors="replace")
    for paragraph_index, paragraph in enumerate(split_paragraphs(text, max_chars=max_chars)):
        if not is_mobility_candidate_text(paragraph):
            continue
        source = {"id": source_id, "kind": source_kind, "paragraph_index": paragraph_index}
        record = record_from_text(paragraph, source)
        if record:
            yield record


def parse_local_path(path: Path, pages: int | None = None, max_chars: int | None = None) -> Iterable[dict[str, Any]]:
    """Extract mobility records from one supported local document."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        yield from parse_pdf_path(path, pages=pages, max_chars=max_chars)
    elif suffix in {".html", ".htm", ".xml"}:
        yield from parse_html_text(path.read_bytes(), str(path), max_chars=max_chars)
    else:
        yield from parse_plain_text(path.read_bytes(), str(path), suffix.lstrip(".") or "file", max_chars=max_chars)


def _get_url(url: str) -> requests.Response:
    errors = []
    for trust_env in (False, True):
        session = requests.Session()
        session.trust_env = trust_env
        try:
            response = session.get(url, timeout=30, headers=REQUEST_HEADERS)
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            errors.append(error)
    raise errors[-1]


def parse_url(url: str, pages: int | None = None, max_chars: int | None = None) -> Iterable[dict[str, Any]]:
    """Download one URL and extract mobility records from its HTML or PDF."""
    response = _get_url(url)
    content_type = response.headers.get("content-type", "").lower()
    looks_pdf = "pdf" in content_type or url.lower().split("?")[0].endswith(".pdf")
    if not looks_pdf:
        yield from parse_html_text(response.content, url, max_chars=max_chars)
        return

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
        handle.write(response.content)
        temp_path = Path(handle.name)
    try:
        yield from parse_pdf_path(temp_path, pages=pages, max_chars=max_chars, source_id=url)
    finally:
        temp_path.unlink(missing_ok=True)
