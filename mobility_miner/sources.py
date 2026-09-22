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

from .extract import extract_mobility_fields, is_mobility_candidate_text, normalized_mobility_item


SUPPORTED_FILE_SUFFIXES = {".html", ".htm", ".xml", ".txt", ".pdf"}
REQUEST_HEADERS = {"User-Agent": "mobility-miner/0.1 (+https://pmc.ncbi.nlm.nih.gov/)"}
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
DOI_FILENAME_RE = re.compile(r"^(10\.\d{4,9})_(.+)$", re.I)
SUPPLEMENTARY_SUFFIX_RE = re.compile(r"_SI\d+$", re.I)
PDF_CONTEXT_METHOD_RE = re.compile(
    r"(?i)\b(?:Hall|OFET|FET|SCLC|TOF|TRMC|TRTS|OPTP|THz|terahertz|"
    r"deformation[-\s]?potential|Boltzmann|Marcus|DFT|first[-\s]?principles?|Drude)\b"
)


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


def split_mobility_passages(text: str) -> Iterable[str]:
    """Build compact sentence-level PDF passages around mobility mentions.

    PDF extractors often return a whole two-column page as one block. Keeping
    that block intact can wrongly attach a DFT mention from the introduction to
    a Hall value later on the page, so PDF evidence is narrowed here before the
    field extractor runs.
    """
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    text = " ".join(text.split())
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
                            yield record
                    paragraph_index += 1
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
