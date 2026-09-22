import json

from mobility_miner.extract import (
    extract_mobility_fields,
    is_mobility_candidate_text,
    normalized_mobility_item,
)
from mobility_miner.report import render_html_report
from mobility_miner.sources import doi_from_pdf_filename, parse_html_text, split_mobility_passages


def _measurements(text):
    fields = extract_mobility_fields(text)
    assert fields is not None
    return fields["mobilities"]


def test_computational_mobility_keeps_algorithm_context_and_span():
    text = (
        "In this work, the room-temperature electron mobility of monolayer MoS2 "
        "was calculated using deformation potential theory to be "
        "2.4 x 10^3 cm^2 V^-1 s^-1 along the armchair direction."
    )

    fields = extract_mobility_fields(text)

    assert fields is not None
    assert fields["materials"][0]["material"] == "monolayer MoS2"
    material = fields["materials"][0]
    assert text[material["span"]["start"] : material["span"]["end"]] == material["raw_text"]
    assert fields["computational_algorithms"][0]["algorithm"] == "deformation-potential theory"
    mobility = fields["mobilities"][0]
    assert mobility["value"] == 2400.0
    assert mobility["carrier"] == "electron"
    assert mobility["temperature"] == "room-temperature"
    assert mobility["direction"] == "armchair"
    assert mobility["material_refs"] == [0]
    assert mobility["determination"] == "computational"
    assert mobility["source_relation"] == "current_work"
    assert text[mobility["span"]["start"] : mobility["span"]["end"]] == mobility["span"]["text"]


def test_experimental_hall_value_converts_square_metres_to_square_centimetres():
    mobility = _measurements(
        "Hall measurements gave a hole mobility of 1.5e-4 m^2 V^-1 s^-1 at 300 K."
    )[0]

    assert mobility["value"] == 1.5
    assert mobility["standard_units"] == "cm^2 V^-1 s^-1"
    assert mobility["carrier"] == "hole"
    assert mobility["temperature"] == "300 K"
    assert mobility["determination"] == "experimental"
    assert mobility["methods"] == ["Hall effect"]


def test_unicode_range_and_prior_work_citation_are_preserved():
    mobility = _measurements(
        "The previously reported mobility was 0.1–0.3 cm² V⁻¹ s⁻¹ [12]."
    )[0]

    assert mobility["value_range"] == [0.1, 0.3]
    assert mobility["raw_units"] == "cm² V⁻¹ s⁻¹"
    assert mobility["source_relation"] == "prior_work"
    assert mobility["determination"] == "reported_unspecified"
    assert mobility["citation_markers"] == ["[12]"]


def test_field_effect_value_with_uncertainty_does_not_turn_value_into_material():
    fields = extract_mobility_fields(
        "Pentacene exhibits a field-effect mobility of 2.1 +/- 0.2 cm2/(V s)."
    )

    assert fields is not None
    assert fields["materials"][0]["material"] == "Pentacene"
    mobility = fields["mobilities"][0]
    assert mobility["value"] == 2.1
    assert mobility["uncertainty"] == 0.2
    assert mobility["methods"] == ["field-effect transistor"]
    assert mobility["material_refs"] == [0]


def test_shared_unit_electron_and_hole_values_are_aligned_in_order():
    text = "The electron and hole mobilities are 1200 and 800 cm^2 V^-1 s^-1, respectively."
    measurements = _measurements(text)

    assert [(item["carrier"], item["value"]) for item in measurements] == [
        ("electron", 1200.0),
        ("hole", 800.0),
    ]
    assert measurements[0]["quantity_span"] == measurements[1]["quantity_span"]
    for item in measurements:
        evidence = item["carrier_evidence"]
        assert text[evidence["span"]["start"] : evidence["span"]["end"]] == evidence["raw_text"]


def test_separate_unit_values_use_nearest_carrier():
    text = (
        "The mobilities are 1200 cm^2 V^-1 s^-1 for electrons and "
        "800 cm^2 V^-1 s^-1 for holes."
    )
    measurements = _measurements(text)

    assert [(item["carrier"], item["value"]) for item in measurements] == [
        ("electron", 1200.0),
        ("hole", 800.0),
    ]
    for item in measurements:
        evidence = item["carrier_evidence"]
        assert text[evidence["span"]["start"] : evidence["span"]["end"]] == evidence["raw_text"]


def test_carriers_in_separate_clauses_bind_to_their_own_values():
    text = (
        "The electron mobility was 10 cm2 V-1 s-1; "
        "the hole mobility was 20 cm2 V-1 s-1."
    )

    measurements = _measurements(text)

    assert [item["carrier"] for item in measurements] == ["electron", "hole"]
    for item in measurements:
        evidence = item["carrier_evidence"]
        assert text[evidence["span"]["start"] : evidence["span"]["end"]] == evidence["raw_text"]


def test_multiple_carriers_without_explicit_alignment_remain_unassigned():
    text = "The electron and hole mobilities were 10 and 20 cm2 V-1 s-1."

    measurements = _measurements(text)

    assert len(measurements) == 2
    assert all("carrier" not in item for item in measurements)
    assert all("multiple_carriers_unaligned" in item["review_flags"] for item in measurements)


def test_method_only_candidate_is_retained_but_does_not_pass_value_filter():
    text = "Charge-carrier mobility was evaluated with time-of-flight measurements."
    fields = extract_mobility_fields(text)

    assert fields is not None
    assert fields["measurement_methods"][0]["method"] == "time-of-flight"
    assert "mobilities" not in fields
    record = normalized_mobility_item({"id": "paper.txt", "kind": "txt"}, text, fields)
    assert record["passes_mobility_filter"] is False


def test_generic_transport_text_is_not_a_mobility_candidate():
    assert not is_mobility_candidate_text("The conductivity increased after iodine doping.")
    assert extract_mobility_fields("The conductivity increased after iodine doping.") is None


def test_html_ingestion_reads_table_rows_and_preserves_source_location():
    html = b"""
    <html><head>
      <meta name="citation_title" content="Transport in COF-5">
      <meta name="citation_doi" content="https://doi.org/10.1234/example.5">
    </head><body><table>
      <tr><th>Material</th><th>Mobility</th></tr>
      <tr><td>COF-5</td><td>Hole mobility: 12 cm2/(V s), measured by SCLC.</td></tr>
    </table></body></html>
    """

    records = list(parse_html_text(html, "memory://table"))

    assert len(records) == 1
    assert records[0]["source"]["element_type"] == "tr"
    assert records[0]["source"]["document_title"] == "Transport in COF-5"
    assert records[0]["source"]["doi"] == "10.1234/example.5"
    assert records[0]["fields"]["materials"][0]["material"] == "COF-5"
    assert records[0]["fields"]["mobilities"][0]["value"] == 12.0
    assert records[0]["fields"]["mobilities"][0]["material_refs"] == [0]
    assert records[0]["fields"]["mobilities"][0]["methods"] == ["space-charge-limited current"]


def test_report_highlights_values_and_escapes_evidence():
    text = "A <sample> mobility was 3.0 cm2/(V s)."
    fields = extract_mobility_fields(text)
    assert fields is not None
    record = normalized_mobility_item({"id": "paper.html", "kind": "html"}, text, fields)

    html = render_html_report([record])

    assert "&lt;sample&gt;" in html
    assert "<sample>" not in html
    assert "<mark>" in html
    assert "Mobility Miner Review Report" in html


def test_normalized_record_is_json_serializable():
    text = "The mobility was calculated to be 5 cm^2 V^-1 s^-1."
    fields = extract_mobility_fields(text)
    assert fields is not None
    record = normalized_mobility_item({"id": "paper.txt", "kind": "txt"}, text, fields)

    encoded = json.dumps(record)

    assert "mobility_miner/0.1" in encoded


def test_pdf_passages_do_not_attach_distant_page_level_algorithm():
    page_text = (
        "DFT was used to analyze an unrelated band structure. "
        "The discussion continued with several structural observations. "
        "Hall measurements gave a hole mobility of 4 cm2/(V s)."
    )

    passages = list(split_mobility_passages(page_text))

    assert passages == ["Hall measurements gave a hole mobility of 4 cm2/(V s)."]
    mobility = extract_mobility_fields(passages[0])["mobilities"][0]
    assert mobility["determination"] == "experimental"
    assert "algorithms" not in mobility


def test_real_corpus_unit_and_method_variants_from_seed_papers():
    uio = _measurements(
        "The mobility of UiO-66(Hf5Zr1) was predicted as 1.4x10−3 cm2/V-s."
    )[0]
    optp = _measurements(
        "Charge-carrier mobility values extracted from OPTP measurements ranged from 13 to 15 cm2V-1s-1."
    )[0]
    trts = _measurements(
        "TRTS gave a mobility of 480 ± 50 cm2·V–1·s–1 using a Drude model."
    )[0]

    assert uio["value"] == 0.0014
    assert optp["value_range"] == [13.0, 15.0]
    assert optp["methods"] == ["terahertz spectroscopy"]
    assert trts["methods"] == ["terahertz spectroscopy"]
    assert trts["analysis_models"] == ["Drude model"]


def test_real_corpus_prose_does_not_create_generic_material_names():
    fields = extract_mobility_fields(
        "Our work shows high charge mobility of 10 cm2V-1s-1 for future logic devices. "
        "This is one of the semiconductors that has exhibited mobility greater than 8 cm2V-1s-1. "
        "Mobility in the ab-plane was calculated as 3 cm2V-1s-1."
    )

    assert fields is not None
    assert "materials" not in fields


def test_corpus_pdf_filenames_provide_auditable_inferred_dois():
    filenames = {
        "10.1038_s41467-026-77017-x.pdf": "10.1038/s41467-026-77017-x",  # COF
        "10.1007_s11664-018-6220-y.pdf": "10.1007/s11664-018-6220-y",  # MOF
        "10.1038_ncomms1451.pdf": "10.1038/ncomms1451",  # organic semiconductor
        "10.1002_adfm.201902656.pdf": "10.1002/adfm.201902656",  # perovskite
        "10.1038_s41467-025-62560-w_SI2.pdf": "10.1038/s41467-025-62560-w",
    }

    assert {name: doi_from_pdf_filename(name) for name in filenames} == filenames
    assert doi_from_pdf_filename("downloaded_article.pdf") is None


def test_cof_effective_mobility_product_is_not_treated_as_direct_mu():
    text = (
        "For PI-DY2DP, the effective mobility (phi placeholder) was "
        "200 cm2 V-1 s-1 and represents a lower bound for mu."
    ).replace("phi placeholder", "\u03c6\u00b7\u03bc").replace("mu", "\u03bc")

    mobility = _measurements(text)[0]

    assert mobility["quantity_kind"] == "mobility_yield_product"
    assert mobility["mobility_relation"]["relation"] == "lower_bound_of_true_mobility"
    label = mobility["quantity_label"]
    assert text[label["span"]["start"] : label["span"]["end"]] == label["raw_text"]
    relation = mobility["mobility_relation"]
    assert text[relation["span"]["start"] : relation["span"]["end"]] == relation["raw_text"]
    assert "reported_quantity_is_not_direct_mobility" in mobility["review_flags"]

    record = normalized_mobility_item({"id": "cof.pdf", "kind": "pdf"}, text, extract_mobility_fields(text))
    report = render_html_report([record])
    assert "mobility_yield_product" in report
    assert "lower_bound_of_true_mobility" in report


def test_perovskite_effective_mobility_without_explicit_phi_stays_unresolved():
    text = "OPTP gave an effective charge-carrier mobility of 13 +/- 2 cm2 V-1 s-1 for the film."

    mobility = _measurements(text)[0]

    assert mobility["quantity_kind"] == "effective_mobility"
    assert "effective_mobility_definition_unresolved" in mobility["review_flags"]
    assert "mobility_relation" not in mobility


def test_pdf_cid_artifact_does_not_hide_phi_mu_product_or_lower_bound():
    text = (
        "We extract an effective mobility (\u03d5(cid:2)\u03bc) of 200 cm2 V-1 s-1; "
        "this valuerepresentsalowerboundfor\u03bc."
    )

    mobility = _measurements(text)[0]

    assert mobility["quantity_kind"] == "mobility_yield_product"
    assert mobility["mobility_relation"]["relation"] == "lower_bound_of_true_mobility"


def test_phi_mu_qualifier_does_not_leak_to_contrasted_direct_mobility():
    text = (
        "The effective mobility \u03c6\u03bc was 200 cm2 V-1 s-1, whereas the direct mobility "
        "was 480 +/- 50 cm2 V-1 s-1."
    )

    measurements = _measurements(text)

    assert measurements[0]["quantity_kind"] == "mobility_yield_product"
    assert "quantity_kind" not in measurements[1]
    assert "reported_quantity_is_not_direct_mobility" not in measurements[1].get("review_flags", [])


def test_fet_operating_regimes_are_bound_to_the_correct_values_with_spans():
    text = (
        "The saturation regime field-effect mobility was 12.3 cm2 V-1 s-1, whereas "
        "the linear regime field-effect mobility was 16.0 cm2 V-1 s-1."
    )

    measurements = _measurements(text)

    assert [item["measurement_regime"]["regime"] for item in measurements] == ["saturation", "linear"]
    for item in measurements:
        regime = item["measurement_regime"]
        assert text[regime["span"]["start"] : regime["span"]["end"]] == regime["raw_text"]


def test_current_and_prior_values_in_one_sentence_keep_separate_provenance():
    text = (
        "We measured a mobility of 12 cm2 V-1 s-1, whereas the previously reported "
        "mobility was 3 cm2 V-1 s-1 [5]."
    )

    measurements = _measurements(text)

    assert [item["source_relation"] for item in measurements] == ["current_work", "prior_work"]
    assert measurements[0]["source_relation_evidence"][0]["cue_type"] == "current_work"
    assert measurements[1]["source_relation_evidence"][0]["cue_type"] == "prior_work"
    for item in measurements:
        for evidence in item["source_relation_evidence"]:
            span = evidence["span"]
            assert text[span["start"] : span["end"]] == evidence["raw_text"]


def test_explicit_current_and_prior_cues_in_same_clause_are_not_forced_to_one_side():
    mobility = _measurements(
        "In this work, the previously reported mobility of the reference was 4 cm2 V-1 s-1."
    )[0]

    assert mobility["source_relation"] == "mixed_or_ambiguous"
    assert "source_relation_mixed_or_ambiguous" in mobility["review_flags"]


def test_temperatures_in_separate_clauses_bind_to_their_own_values():
    text = (
        "At 300 K, the electron mobility was 10 cm2 V-1 s-1; "
        "at 400 K, it was 20 cm2 V-1 s-1."
    )

    measurements = _measurements(text)

    assert [item["temperature"] for item in measurements] == ["300 K", "400 K"]
    for item in measurements:
        evidence = item["temperature_evidence"]
        assert text[evidence["span"]["start"] : evidence["span"]["end"]] == evidence["raw_text"]


def test_multiple_temperatures_in_one_clause_are_not_assigned_by_first_match():
    text = "At 300 K and 400 K, mobilities were 10 and 20 cm2 V-1 s-1, respectively."

    measurements = _measurements(text)

    assert len(measurements) == 2
    assert all("temperature" not in item for item in measurements)
    assert all("multiple_temperatures_unaligned" in item["review_flags"] for item in measurements)


def test_directions_in_separate_clauses_bind_to_their_own_values():
    text = (
        "The armchair mobility was 10 cm2 V-1 s-1; "
        "the zigzag mobility was 20 cm2 V-1 s-1."
    )

    measurements = _measurements(text)

    assert [item["direction"] for item in measurements] == ["armchair", "zigzag"]
    for item in measurements:
        evidence = item["direction_evidence"]
        assert text[evidence["span"]["start"] : evidence["span"]["end"]] == evidence["raw_text"]


def test_multiple_directions_in_one_clause_remain_unaligned():
    text = "Along armchair and zigzag directions, mobilities were 10 and 20 cm2 V-1 s-1, respectively."

    measurements = _measurements(text)

    assert len(measurements) == 2
    assert all("direction" not in item for item in measurements)
    assert all("multiple_directions_unaligned" in item["review_flags"] for item in measurements)


def test_experimental_methods_in_contrast_clauses_bind_to_their_own_values():
    text = (
        "Hall mobility was 10 cm2 V-1 s-1, whereas "
        "FET mobility was 20 cm2 V-1 s-1."
    )

    measurements = _measurements(text)

    assert [item["methods"] for item in measurements] == [
        ["Hall effect"],
        ["field-effect transistor"],
    ]
    assert [item["determination"] for item in measurements] == ["experimental", "experimental"]
    for item in measurements:
        evidence = item["method_evidence"][0]
        assert text[evidence["span"]["start"] : evidence["span"]["end"]] == evidence["raw_text"]


def test_computational_algorithms_in_semicolon_clauses_bind_to_their_own_values():
    text = (
        "Deformation-potential theory gave mobility 100 cm2 V-1 s-1; "
        "Marcus theory gave mobility 1 cm2 V-1 s-1."
    )

    measurements = _measurements(text)

    assert [item["algorithms"] for item in measurements] == [
        ["deformation-potential theory"],
        ["Marcus theory"],
    ]
    assert [item["determination"] for item in measurements] == ["computational", "computational"]
    for item in measurements:
        evidence = item["algorithm_evidence"][0]
        assert text[evidence["span"]["start"] : evidence["span"]["end"]] == evidence["raw_text"]
