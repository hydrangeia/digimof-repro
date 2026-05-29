"""Download article HTML/PDF files for local framework extraction."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


REQUEST_HEADERS = {"User-Agent": "framework-miner/0.1 (+https://pmc.ncbi.nlm.nih.gov/)"}
DOI_RE = re.compile(r"^(?:doi:\s*)?(10\.\d{4,9}/\S+)$", flags=re.I)
RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def normalize_identifier(identifier: str) -> str:
    value = identifier.strip()
    if value.lower().startswith(("http://", "https://")):
        return value
    if value.lower().startswith(("doi.org/", "dx.doi.org/")):
        return "https://{}".format(value)

    match = DOI_RE.match(value)
    if match:
        doi = match.group(1).strip().rstrip(".,;")
        return "https://doi.org/{}".format(doi)

    raise ValueError("not a URL or DOI: {}".format(identifier))


def fetch_url(url: str) -> requests.Response:
    errors: list[requests.RequestException] = []
    for trust_env in (False, True):
        session = requests.Session()
        session.trust_env = trust_env
        try:
            response = session.get(url, timeout=45, headers=REQUEST_HEADERS)
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            errors.append(error)
    raise errors[-1]


def safe_filename(text: str, default: str = "article") -> str:
    text = re.sub(r"\s+", "_", text.strip())
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    text = text.strip("._-")
    if not text:
        text = default
    if text.upper() in RESERVED_NAMES:
        text = "{}_article".format(text)
    return text[:120]


def title_from_html(content: bytes) -> str | None:
    soup = BeautifulSoup(content, "html.parser")
    if soup.title:
        title = " ".join(soup.title.get_text(" ").split())
        if title:
            return title
    heading = soup.find("h1")
    if heading:
        title = " ".join(heading.get_text(" ").split())
        if title:
            return title
    return None


def filename_for_url(url: str, content: bytes, content_type: str, index: int) -> str:
    parsed = urlparse(url)
    path_name = Path(parsed.path.rstrip("/")).name
    suffix = ".pdf" if "pdf" in content_type.lower() or path_name.lower().endswith(".pdf") else ".html"

    if suffix == ".html":
        title = title_from_html(content)
        if title:
            return "{}{}".format(safe_filename(title), suffix)

    stem = safe_filename(path_name or parsed.netloc or "article", default="article_{}".format(index))
    if stem.lower().endswith((".html", ".htm", ".pdf")):
        stem = Path(stem).stem
    return "{}{}".format(stem, suffix)


def unique_path(path: Path, overwrite: bool) -> Path:
    if overwrite or not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = path.with_name("{}_{}{}".format(stem, index, suffix))
        if not candidate.exists():
            return candidate
    raise RuntimeError("Could not choose a unique path for {}".format(path))


def iter_identifiers(args: argparse.Namespace) -> list[tuple[str, str]]:
    raw_values = list(args.identifiers)
    if args.url_file:
        for line in args.url_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                raw_values.append(line)
    if args.doi_file:
        for line in args.doi_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                raw_values.append(line)
    return [(value, normalize_identifier(value)) for value in raw_values]


def main() -> None:
    parser = argparse.ArgumentParser(description="Download article HTML/PDF files for local DigiMOF reproduction.")
    parser.add_argument("identifiers", nargs="*", help="Article URLs or DOI strings to download.")
    parser.add_argument("--url-file", type=Path, help="UTF-8 text file with one URL or DOI per line.")
    parser.add_argument("--doi-file", type=Path, help="UTF-8 text file with one DOI per line.")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("downloaded_articles"))
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files instead of adding a suffix.")
    args = parser.parse_args()

    identifiers = iter_identifiers(args)
    if not identifiers:
        parser.error("provide at least one URL/DOI, --url-file, or --doi-file")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "manifest.jsonl"
    written = []
    with manifest_path.open("a", encoding="utf-8") as manifest:
        for index, (raw_identifier, url) in enumerate(identifiers, start=1):
            response = fetch_url(url)
            content_type = response.headers.get("content-type", "")
            filename = filename_for_url(url, response.content, content_type, index)
            output_path = unique_path(args.output_dir / filename, overwrite=args.overwrite)
            output_path.write_bytes(response.content)
            record = {
                "input": raw_identifier,
                "url": url,
                "final_url": response.url,
                "path": str(output_path),
                "content_type": content_type,
                "bytes": len(response.content),
            }
            manifest.write(json.dumps(record, ensure_ascii=False) + "\n")
            written.append(output_path)

    for path in written:
        print(path)


if __name__ == "__main__":
    main()
