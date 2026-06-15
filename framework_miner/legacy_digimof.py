"""Normalized extraction helpers built around the legacy DigiMOF parser stack."""

from __future__ import annotations

import io
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text

from .bootstrap import LEGACY_ROOT, PROJECT_ROOT, ensure_repo_environment
from .cof import heuristic_cof_fields, is_cof_candidate_text, normalized_cof_item

ensure_repo_environment()

from chemdataextractor import Document  # noqa: E402
from chemdataextractor.doc import Paragraph  # noqa: E402
from MOF_database import reobj  # noqa: E402


SUPPORTED_FILE_SUFFIXES = {".html", ".htm", ".xml", ".txt", ".pdf"}
OBVIOUS_FALSE_MOF_NAMES = {
    "CSD",
    "DFT",
    "ML",
    "SI",
}
SYNTHESIS_TERMS = [
    "solvothermal",
    "hydrothermal",
    "ionothermal",
    "mechanochemical",
    "electrochemical",
    "sonochemical",
    "ultrasonic-assisted",
    "microwave-assisted",
    "plasma in liquid",
]
MOF_PARAGRAPH_TERMS = [
    "mof",
    "metal-organic framework",
    "metal–organic framework",
    "metal organic framework",
    "solvothermal",
    "hydrothermal",
    "ionothermal",
    "mechanochemical",
]
MOF_CONTEXT_BOUNDARY = (
    r"(?=,\s*(?:which|that|was|were|has|have|is|are|can|with|featuring)\b"
    r"|;\s*|\.\s+[A-Z]|$)"
)
MOF_DESCRIPTOR_PATTERN = r"metal(?:[^A-Za-z0-9]{0,4})organic\s+framework"
REQUEST_HEADERS = {"User-Agent": "framework-miner/0.1 (+https://pmc.ncbi.nlm.nih.gov/)"}


def clean_heuristic_name(raw_name: str) -> str:
    name = " ".join(raw_name.split())
    return name.strip(" \t\r\n,.;")


def iter_local_inputs(inputs: Iterable[str | Path]) -> Iterable[Path]:
    for item in inputs:
        path = Path(item)
        if path.is_dir():
            for suffix in SUPPORTED_FILE_SUFFIXES:
                yield from sorted(path.rglob("*{}".format(suffix)))
        elif path.is_file() and path.suffix.lower() in SUPPORTED_FILE_SUFFIXES:
            yield path


def split_paragraphs(text: str, max_chars: int | None = None) -> Iterable[str]:
    if max_chars:
        text = text[:max_chars]
    for chunk in re.split(r"\n\s*\n+", text):
        paragraph = " ".join(chunk.split())
        if len(paragraph) >= 40:
            yield paragraph


def is_mof_candidate_text(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in MOF_PARAGRAPH_TERMS)


def is_candidate_text(text: str, framework: str = "mof") -> bool:
    if framework == "mof":
        return is_mof_candidate_text(text)
    if framework == "cof":
        return is_cof_candidate_text(text)
    return is_mof_candidate_text(text) or is_cof_candidate_text(text)


def record_names(record: dict) -> list[str]:
    return [name for name in record.get("names", []) if isinstance(name, str)]


def is_mof_record(record: dict) -> bool:
    return any(
        name not in OBVIOUS_FALSE_MOF_NAMES and re.search(reobj, name)
        for name in record_names(record)
    )


def compact_fields(record: dict) -> dict:
    fields = {"names": record_names(record)}
    if record.get("synthesis_routes"):
        fields["synthesis_routes"] = record["synthesis_routes"]
    if record.get("topologies"):
        fields["topologies"] = record["topologies"]
    if record.get("linker_routes"):
        fields["linker_routes"] = record["linker_routes"]
    return fields


def digimof_shape_from_fields(source_id: str, fields: dict) -> dict:
    mof_data = {
        "file": source_id,
        "compound": {"Compound": {"names": fields.get("names", [])}},
    }
    if fields.get("synthesis_routes"):
        mof_data["synthesis_route"] = fields["synthesis_routes"]
    if fields.get("topologies"):
        topology = fields["topologies"][0]
        if isinstance(topology, dict):
            mof_data["topology"] = topology.get("abrv")
    if fields.get("linker_routes"):
        mof_data["linker"] = fields["linker_routes"]
    return {"MOF_data": mof_data}


def digimof_shape(source_id: str, record: dict) -> dict:
    return digimof_shape_from_fields(source_id, compact_fields(record))


def normalized_item(source: dict, evidence_text: str, record: dict) -> dict:
    passes_mof_filter = is_mof_record(record)
    item = {
        "schema_version": "framework_miner/0.1",
        "framework_type": "MOF",
        "source": source,
        "evidence_text": evidence_text,
        "fields": compact_fields(record),
        "raw_record": record,
        "passes_mof_filter": passes_mof_filter,
        "passes_framework_filter": passes_mof_filter,
    }
    if item["passes_mof_filter"]:
        item.update(digimof_shape(source.get("id", ""), record))
    return item


def heuristic_mof_fields(text: str) -> dict | None:
    names: list[str] = []
    patterns = [
        (r"\(MOF,\s*([^)]+)\)", re.I),
        (
            (
                r"(?i:{}\s*\(MOF\),\s*)".format(MOF_DESCRIPTOR_PATTERN)
                + r"([A-Z{].+?)(?=,\s*(?:which|that|was|were|has|have|is|are|can|with|featuring)\b|;\s*|\.(?:\s+[A-Z]|$)|$)"
            ),
            0,
        ),
        (
            (
                r"([A-Z](?=[A-Za-z0-9{}\[\]()/,+.\-\s]{1,80}?\d)"
                r"[A-Za-z0-9{}\[\]()/,+.\-\s]{1,80}?)\s+"
                + r"(?i:is\s+(?:an?\s+)?(?:[^.]{{0,120}}?){}\s*\(MOF\))".format(MOF_DESCRIPTOR_PATTERN)
            ),
            0,
        ),
        (
            r"(?i:\b(?:we\s+)?(?:prepared|synthesized|obtained|formed|isolated)\s+)"
            r"([A-Z][A-Za-z0-9(){}\[\]/,+.\-]{1,60}MOF(?:\s*\([^)]+\))?)"
            r"(?=\s+(?:using|via|by|through|from|under|with|at|in)\b|[,.;\)]|$)",
            0,
        ),
        (
            r"([A-Z][A-Za-z0-9(){}\[\]/,+.\-]{1,60}MOF(?:\s*\([^)]+\))?)\s+"
            r"(?i:(?:was|were|is|are)\s+(?:prepared|synthesized|obtained|formed|isolated))"
            r"(?=\s+(?:using|via|by|through|from|under|with|at|in)\b|[,.;\)]|$)",
            0,
        ),
    ]
    for pattern, flags in patterns:
        for match in re.finditer(pattern, text, flags=flags):
            name = clean_heuristic_name(match.group(1))
            if len(name) >= 3 and name not in names:
                names.append(name)

    if not names:
        return None

    fields: dict = {"names": names}
    lower = text.lower()
    synthesis_routes = [{"synthesis": term} for term in SYNTHESIS_TERMS if term in lower]
    if synthesis_routes:
        fields["synthesis_routes"] = synthesis_routes
    return fields


def normalized_heuristic_item(source: dict, evidence_text: str, fields: dict) -> dict:
    item = {
        "schema_version": "framework_miner/0.1",
        "framework_type": "MOF",
        "source": source,
        "evidence_text": evidence_text,
        "fields": fields,
        "passes_mof_filter": True,
        "passes_framework_filter": True,
        "extraction_method": "paragraph_heuristic",
    }
    item.update(digimof_shape_from_fields(source.get("id", ""), fields))
    return item


def _append_unique(values: list, new_values: list) -> list:
    for value in new_values:
        if value not in values:
            values.append(value)
    return values


def merge_items(items: Iterable[dict]) -> Iterable[dict]:
    merged: dict[tuple, dict] = {}
    order: list[tuple] = []
    for item in items:
        fields = item.get("fields", {})
        names = tuple(fields.get("names", []))
        key = (item["source"].get("id"), item.get("framework_type"), names)
        if key not in merged:
            new_item = dict(item)
            raw_record = new_item.pop("raw_record", None)
            if raw_record is not None:
                new_item["raw_records"] = [raw_record]
            evidence_text = new_item.get("evidence_text")
            new_item["evidence_texts"] = [evidence_text] if evidence_text else []
            merged[key] = new_item
            order.append(key)
            continue

        target = merged[key]
        target["passes_mof_filter"] = bool(target.get("passes_mof_filter") or item.get("passes_mof_filter"))
        target["passes_framework_filter"] = bool(
            target.get("passes_framework_filter") or item.get("passes_framework_filter")
        )
        evidence_text = item.get("evidence_text")
        if evidence_text and evidence_text not in target.setdefault("evidence_texts", []):
            target["evidence_texts"].append(evidence_text)
        raw_record = item.get("raw_record")
        if raw_record is not None:
            target.setdefault("raw_records", []).append(raw_record)
        target_fields = target.setdefault("fields", {})
        for field_name, values in fields.items():
            if isinstance(values, list):
                target_fields[field_name] = _append_unique(target_fields.setdefault(field_name, []), values)
            elif field_name not in target_fields:
                target_fields[field_name] = values

    for key in order:
        item = merged[key]
        item.pop("MOF_data", None)
        if item.get("passes_mof_filter"):
            item.update(digimof_shape_from_fields(item["source"].get("id", ""), item.get("fields", {})))
        yield item


def records_from_document(doc: Document, source: dict, framework: str = "mof") -> Iterable[dict]:
    for element_index, element in enumerate(doc.elements):
        if not hasattr(element, "records"):
            continue
        evidence_text = str(element)

        if framework in {"mof", "all"}:
            records = element.records
            serialized = records.serialize() if hasattr(records, "serialize") else records
            for record in serialized:
                if record:
                    enriched_source = dict(source)
                    enriched_source["element_index"] = element_index
                    yield normalized_item(enriched_source, evidence_text, record)
            heuristic_fields = heuristic_mof_fields(evidence_text)
            if heuristic_fields:
                enriched_source = dict(source)
                enriched_source["element_index"] = element_index
                yield normalized_heuristic_item(enriched_source, evidence_text, heuristic_fields)

        if framework in {"cof", "all"}:
            cof_fields = heuristic_cof_fields(evidence_text)
            if cof_fields:
                enriched_source = dict(source)
                enriched_source["element_index"] = element_index
                yield normalized_cof_item(enriched_source, evidence_text, cof_fields)


def records_from_text(text: str, source: dict, framework: str = "mof") -> Iterable[dict]:
    if framework in {"mof", "all"}:
        doc = Document(Paragraph(text))
        yield from records_from_document(doc, source, framework=framework)
    elif framework == "cof":
        cof_fields = heuristic_cof_fields(text)
        if cof_fields:
            enriched_source = dict(source)
            enriched_source["element_index"] = 0
            yield normalized_cof_item(enriched_source, text, cof_fields)


def parse_structured_bytes(content: bytes, source_id: str, source_kind: str, framework: str = "mof") -> Iterable[dict]:
    doc = Document.from_file(io.BytesIO(content), fname=source_id)
    source = {"id": source_id, "kind": source_kind}
    yield from records_from_document(doc, source, framework=framework)


def parse_html_text(
    content: bytes,
    source_id: str,
    max_chars: int | None = None,
    framework: str = "mof",
) -> Iterable[dict]:
    soup = BeautifulSoup(content, "html.parser")
    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
        element.decompose()

    paragraphs = []
    for tag in soup.find_all(["h1", "h2", "h3", "p"]):
        text = " ".join(tag.get_text(" ").split())
        if len(text) >= 40:
            paragraphs.append(text)

    used_chars = 0
    source = {"id": source_id, "kind": "url_html"}
    for paragraph_index, paragraph in enumerate(paragraphs):
        if not is_candidate_text(paragraph, framework=framework):
            continue
        if max_chars and used_chars >= max_chars:
            break
        if max_chars and used_chars + len(paragraph) > max_chars:
            paragraph = paragraph[: max_chars - used_chars]
        used_chars += len(paragraph)
        for item in records_from_text(paragraph, source, framework=framework):
            item["source"]["paragraph_index"] = paragraph_index
            yield item


def parse_pdf_path(
    path: Path,
    pages: int | None = None,
    max_chars: int | None = None,
    source_id: str | None = None,
    framework: str = "mof",
) -> Iterable[dict]:
    page_numbers = range(pages) if pages else None
    text = extract_text(str(path), page_numbers=page_numbers)
    source = {"id": source_id or str(path), "kind": "pdf"}
    for paragraph_index, paragraph in enumerate(split_paragraphs(text, max_chars=max_chars)):
        if not is_candidate_text(paragraph, framework=framework):
            continue
        for item in records_from_text(paragraph, source, framework=framework):
            item["source"]["paragraph_index"] = paragraph_index
            yield item


def parse_local_path(
    path: Path,
    pages: int | None = None,
    max_chars: int | None = None,
    framework: str = "mof",
) -> Iterable[dict]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        yield from parse_pdf_path(path, pages=pages, max_chars=max_chars, framework=framework)
    elif suffix in {".html", ".htm"}:
        yield from parse_html_text(path.read_bytes(), str(path), max_chars=max_chars, framework=framework)
    else:
        yield from parse_structured_bytes(path.read_bytes(), str(path), suffix.lstrip(".") or "file", framework=framework)


def parse_url(
    url: str,
    pages: int | None = None,
    max_chars: int | None = None,
    framework: str = "mof",
) -> Iterable[dict]:
    errors: list[requests.RequestException] = []
    response = None
    for trust_env in (False, True):
        session = requests.Session()
        session.trust_env = trust_env
        try:
            response = session.get(url, timeout=30, headers=REQUEST_HEADERS)
            response.raise_for_status()
            break
        except requests.RequestException as error:
            errors.append(error)

    if response is None:
        raise errors[-1]

    content_type = response.headers.get("content-type", "").lower()
    looks_pdf = "pdf" in content_type or url.lower().split("?")[0].endswith(".pdf")
    if looks_pdf:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            handle.write(response.content)
            temp_path = Path(handle.name)
        try:
            yield from parse_pdf_path(temp_path, pages=pages, max_chars=max_chars, source_id=url, framework=framework)
        finally:
            temp_path.unlink(missing_ok=True)
    else:
        yield from parse_html_text(response.content, url, max_chars=max_chars, framework=framework)


def write_jsonl(
    items: Iterable[dict],
    output: Path,
    mof_only: bool = False,
    framework_only: bool = False,
) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8") as handle:
        for item in items:
            if mof_only and not item.get("passes_mof_filter"):
                continue
            if framework_only and not (item.get("passes_mof_filter") or item.get("passes_framework_filter")):
                continue
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            count += 1
    return count
