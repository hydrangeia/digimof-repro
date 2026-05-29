from argparse import Namespace
from pathlib import Path

import pytest

from download_article_html import iter_identifiers, normalize_identifier


def test_normalize_identifier_keeps_url():
    assert normalize_identifier("https://pmc.ncbi.nlm.nih.gov/articles/PMC9085643/") == (
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC9085643/"
    )


def test_normalize_identifier_accepts_bare_doi():
    assert normalize_identifier("10.1039/D1RA00942G") == "https://doi.org/10.1039/D1RA00942G"


def test_normalize_identifier_accepts_doi_prefix():
    assert normalize_identifier("doi: 10.1002/anie.201811399.") == (
        "https://doi.org/10.1002/anie.201811399"
    )


def test_normalize_identifier_accepts_doi_domain_without_scheme():
    assert normalize_identifier("doi.org/10.1039/D1RA00942G") == "https://doi.org/10.1039/D1RA00942G"


def test_normalize_identifier_rejects_plain_text():
    with pytest.raises(ValueError):
        normalize_identifier("not a paper id")


def test_iter_identifiers_reads_url_and_doi_files(tmp_path: Path):
    url_file = tmp_path / "urls.txt"
    doi_file = tmp_path / "dois.txt"
    url_file.write_text("# comment\nhttps://example.org/article\n", encoding="utf-8")
    doi_file.write_text("10.1039/D1RA00942G\n", encoding="utf-8")
    args = Namespace(identifiers=["10.1002/anie.201811399"], url_file=url_file, doi_file=doi_file)

    identifiers = iter_identifiers(args)

    assert identifiers == [
        ("10.1002/anie.201811399", "https://doi.org/10.1002/anie.201811399"),
        ("https://example.org/article", "https://example.org/article"),
        ("10.1039/D1RA00942G", "https://doi.org/10.1039/D1RA00942G"),
    ]
