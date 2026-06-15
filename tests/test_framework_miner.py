from pathlib import Path

from framework_miner.legacy_digimof import (
    heuristic_mof_fields,
    is_mof_candidate_text,
    merge_items,
    parse_local_path,
    parse_html_text,
)


def test_heuristic_mof_name_keeps_decimal_hydrate():
    text = (
        "A metal-organic framework (MOF), {(H 3 O + ) 2 "
        "[Ca(NDC)(C 2 H 5 O)(OH)]} 4 路1.1H2O, was synthesized "
        "under solvothermal conditions."
    )

    fields = heuristic_mof_fields(text)

    assert fields is not None
    assert fields["names"] == ["{(H 3 O + ) 2 [Ca(NDC)(C 2 H 5 O)(OH)]} 4 路1.1H2O"]
    assert fields["synthesis_routes"] == [{"synthesis": "solvothermal"}]


def test_heuristic_mof_parenthetical_name():
    fields = heuristic_mof_fields("A crystalline framework (MOF, HKUST-1) was obtained.")

    assert fields is not None
    assert fields["names"] == ["HKUST-1"]


def test_heuristic_mof_newer_synthesis_terms():
    text = "A metal-organic framework (MOF), UiO-66, was prepared by ionothermal synthesis."

    fields = heuristic_mof_fields(text)

    assert fields is not None
    assert fields["synthesis_routes"] == [{"synthesis": "ionothermal"}]


def test_heuristic_mof_handles_metal_organic_without_hyphen():
    text = "A metal organic framework (MOF), ZIF-8, was prepared by mechanochemical synthesis."

    fields = heuristic_mof_fields(text)

    assert fields is not None
    assert fields["names"] == ["ZIF-8"]
    assert fields["synthesis_routes"] == [{"synthesis": "mechanochemical"}]


def test_heuristic_mof_handles_name_before_mof_descriptor():
    text = (
        "MIL-100 (Fe) is a highly porous metal-organic framework (MOF), considered as "
        "a promising carrier for drug delivery, and for gas separation and capture "
        "applications. Herein, we report a green mechanochemical water immersion "
        "approach to yield highly crystalline MIL100 (Fe) material."
    )

    fields = heuristic_mof_fields(text)

    assert fields is not None
    assert fields["names"] == ["MIL-100 (Fe)"]
    assert fields["synthesis_routes"] == [{"synthesis": "mechanochemical"}]


def test_heuristic_mof_handles_direct_name_in_experimental_paragraph():
    text = (
        "We prepared CaNDC-MOF using a solvothermal synthesis method. "
        "Calcium(II) acetylacetonate and H2NDC were mixed in an aqueous solution of ethanol "
        "with stirring for 60 min. The mixed solution was placed in a vial and sealed, then "
        "kept in an oven at 100 掳C for 7 days."
    )

    fields = heuristic_mof_fields(text)

    assert fields is not None
    assert fields["names"] == ["CaNDC-MOF"]
    assert fields["synthesis_routes"] == [{"synthesis": "solvothermal"}]


def test_heuristic_mof_handles_formula_name_after_descriptor():
    text = (
        "The solvothermal reaction of a mixture of calcium acetylacetonate and "
        "1,4-naphthalenedicarboxylic acid (H 2 NDC) in a solution containing ethanol "
        "and distilled water gave rise to a metal-organic framework (MOF), "
        "{(H 3 O + ) 2 [Ca(NDC)(C 2 H 5 O)(OH)]} 4 路1.1H 2 O."
    )

    fields = heuristic_mof_fields(text)

    assert fields is not None
    assert fields["names"] == ["{(H 3 O + ) 2 [Ca(NDC)(C 2 H 5 O)(OH)]} 4 路1.1H 2 O"]
    assert fields["synthesis_routes"] == [{"synthesis": "solvothermal"}]


def test_mof_candidate_text_filters_generic_page_chrome():
    assert not is_mof_candidate_text("Official websites use .gov for a government organization.")
    assert is_mof_candidate_text("A calcium-based metal-organic framework was synthesized.")


def test_parse_html_text_counts_only_candidate_paragraphs():
    html = b"""
    <html><body>
      <p>Official websites use .gov for a government organization in the United States.</p>
      <p>The solvothermal reaction gave rise to a metal-organic framework (MOF), CaNDC-MOF.</p>
    </body></html>
    """

    records = list(parse_html_text(html, "memory://paper", max_chars=120))

    assert any(record.get("passes_mof_filter") for record in records)
    assert all(".gov" not in record["evidence_text"] for record in records)


def test_parse_local_sample_html_extracts_legacy_digimof_record():
    records = list(merge_items(parse_local_path(Path("sample_inputs/ntu105.html"))))
    matching = [
        record
        for record in records
        if record.get("passes_mof_filter")
        and "NTU-105-NH2" in record.get("fields", {}).get("names", [])
    ]

    assert len(matching) == 1
    fields = matching[0]["fields"]
    assert fields["synthesis_routes"] == [{"synthesis": "solvothermal"}]
    assert fields["topologies"] == [{"abrv": "rht"}]
    assert fields["linker_routes"] == [{"linker": "['hexacarboxylate']"}]


def test_merge_items_accepts_heuristic_without_raw_record():
    item = {
        "schema_version": "framework_miner/0.1",
        "framework_type": "MOF",
        "source": {"id": "paper.html", "kind": "url_html"},
        "evidence_text": "A metal-organic framework (MOF), HKUST-1, was synthesized.",
        "fields": {"names": ["HKUST-1"], "synthesis_routes": [{"synthesis": "solvothermal"}]},
        "passes_mof_filter": True,
        "extraction_method": "paragraph_heuristic",
    }

    merged = list(merge_items([item]))

    assert len(merged) == 1
    assert "raw_records" not in merged[0]
    assert merged[0]["MOF_data"]["compound"]["Compound"]["names"] == ["HKUST-1"]


def test_merge_items_deduplicates_same_material_across_evidence():
    base_item = {
        "schema_version": "framework_miner/0.1",
        "framework_type": "MOF",
        "source": {"id": "paper.html", "kind": "url_html"},
        "fields": {"names": ["CaNDC-MOF"], "synthesis_routes": [{"synthesis": "solvothermal"}]},
        "passes_mof_filter": True,
        "extraction_method": "paragraph_heuristic",
    }
    first = dict(base_item, evidence_text="CaNDC-MOF was reported in the abstract.")
    second = dict(base_item, evidence_text="CaNDC-MOF was synthesized in the experimental section.")

    merged = list(merge_items([first, second]))

    assert len(merged) == 1
    assert merged[0]["evidence_texts"] == [
        "CaNDC-MOF was reported in the abstract.",
        "CaNDC-MOF was synthesized in the experimental section.",
    ]
