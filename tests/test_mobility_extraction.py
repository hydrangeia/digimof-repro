import json

from mobility_miner.extract import (
    extract_mobility_fields,
    is_mobility_candidate_text,
    normalized_mobility_item,
)
from mobility_miner.report import render_html_report
from mobility_miner.sources import (
    _link_page_fabrication_conditions,
    doi_from_pdf_filename,
    parse_html_text,
    record_from_text,
    split_mobility_passages,
)


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
    material_condition = next(
        item for item in mobility["condition_records"] if item["field"] == "material_identity"
    )
    assert material_condition["value"] == "Pentacene"
    assert material_condition["binding_scope"] == "material"
    coverage = {item["field"]: item["status"] for item in mobility["condition_coverage"]}
    assert coverage["material_identity"] == "reported"
    assert coverage["synthesis_processing"] == "not_reported"


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


def test_review_status_distinguishes_ready_review_and_blocked_measurements():
    ready = _measurements(
        "In this work, Pentacene exhibits a field-effect mobility of 1.2 cm2 V-1 s-1."
    )[0]
    review = _measurements(
        "Pentacene exhibits a field-effect mobility of 1.2 cm2 V-1 s-1."
    )[0]
    blocked = _measurements(
        "In this work, the Hall mobility was 1.2 cm2 V-1 s-1."
    )[0]

    assert ready["review_status"] == "READY"
    assert "review_status_reasons" not in ready
    assert review["review_status"] == "REVIEW"
    assert review["review_status_reasons"] == ["source_relation_unspecified"]
    assert blocked["review_status"] == "BLOCKED"
    assert "material_unresolved" in blocked["review_status_reasons"]

    blocked_text = "In this work, the Hall mobility was 1.2 cm2 V-1 s-1."
    fields = extract_mobility_fields(blocked_text)
    assert fields is not None
    record = normalized_mobility_item(
        {"id": "blocked.pdf", "kind": "pdf"},
        blocked_text,
        fields,
    )
    assert "BLOCKED" in render_html_report([record])


def test_html_report_counts_and_searches_measurement_review_statuses():
    texts = [
        "In this work, Pentacene exhibits a field-effect mobility of 1.2 cm2 V-1 s-1.",
        "Pentacene exhibits a field-effect mobility of 1.2 cm2 V-1 s-1.",
        "In this work, the Hall mobility was 1.2 cm2 V-1 s-1.",
    ]
    records = []
    for index, text in enumerate(texts):
        fields = extract_mobility_fields(text)
        assert fields is not None
        records.append(
            normalized_mobility_item(
                {"id": "status-{}.pdf".format(index), "kind": "pdf"},
                text,
                fields,
            )
        )

    report = render_html_report(records)

    assert "<strong>1</strong>ready" in report
    assert "<strong>1</strong>review" in report
    assert "<strong>1</strong>blocked" in report
    assert "source_relation_unspecified" in report


def test_each_normalized_measurement_carries_its_source_locator_and_exact_span():
    text = "Figure 3C displays a mobility of 13 cm2 V-1 s-1."
    fields = extract_mobility_fields(text)
    assert fields is not None
    source = {
        "id": "paper.pdf",
        "kind": "pdf",
        "page": 7,
        "paragraph_index": 15,
        "doi": "10.1002/example",
        "doi_source": "embedded",
    }

    record = normalized_mobility_item(source, text, fields)
    evidence_ref = record["fields"]["mobilities"][0]["evidence_refs"][0]

    assert evidence_ref["source_id"] == "paper.pdf"
    assert evidence_ref["page"] == 7
    assert evidence_ref["paragraph_index"] == 15
    assert evidence_ref["doi"] == "10.1002/example"
    span = evidence_ref["span"]
    assert text[span["start"] : span["end"]] == span["text"]


def test_document_locators_are_bound_within_each_measurement_clause():
    text = (
        "Figure 3C gives a mobility of 13 cm2 V-1 s-1; "
        "Table S2 gives a mobility of 4 cm2 V-1 s-1."
    )

    measurements = _measurements(text)

    assert [[item["raw_text"] for item in measurement["document_locators"]] for measurement in measurements] == [
        ["Figure 3C"],
        ["Table S2"],
    ]
    for measurement in measurements:
        locator = measurement["document_locators"][0]
        assert text[locator["span"]["start"] : locator["span"]["end"]] == locator["raw_text"]


def test_block_locator_without_clause_level_link_stays_unaligned():
    fields = extract_mobility_fields(
        "Figure 2 shows the sample morphology. The mobility was 4 cm2 V-1 s-1."
    )

    assert fields is not None
    assert fields["document_locators"][0]["raw_text"] == "Figure 2"
    mobility = fields["mobilities"][0]
    assert "document_locators" not in mobility
    assert "document_locator_unaligned" in mobility["review_flags"]


def test_citation_alone_does_not_turn_an_unresolved_value_into_prior_work():
    mobility = _measurements(
        "The mobility was 13 cm2 V-1 s-1, within the range needed for devices.[49]"
    )[0]

    assert mobility["citation_markers"] == ["[49]"]
    assert mobility["source_relation"] == "unspecified"
    assert "source_relation_evidence" not in mobility


def test_current_measurement_compared_with_prior_values_stays_current_work():
    text = (
        "Effective charge-carrier mobility: The measured value of 13 ± 2 cm2 V-1 s-1 "
        "for the BA-free composition "
        "is in excellent agreement with previously reported values.[36]"
    )

    mobility = _measurements(text)[0]

    assert mobility["source_relation"] == "current_work"
    assert [item["cue_type"] for item in mobility["source_relation_evidence"]] == [
        "current_work"
    ]
    cue = mobility["source_relation_evidence"][0]
    assert text[cue["span"]["start"] : cue["span"]["end"]] == "The measured value"
    assert mobility["citation_markers"] == ["[36]"]


def test_pdf_column_artifact_containing_supporting_information_is_not_a_material():
    text = (
        "The measured mobility was 13 ± 2 cm2 V-1 s-1. "
        "There have been reports of charge-carrier mobilities in Rud0 tion given "
        "in the Supporting Information)."
    )

    fields = extract_mobility_fields(text)

    assert fields is not None
    assert "materials" not in fields
    mobility = fields["mobilities"][0]
    assert "material_refs" not in mobility
    assert "material_unresolved" in mobility["review_flags"]
    coverage = {item["field"]: item["status"] for item in mobility["condition_coverage"]}
    assert coverage["material_identity"] == "not_reported"


def test_explicit_film_sample_form_binds_within_the_mobility_clause():
    text = (
        "OPTP measurements for films of the perovskite gave an effective mobility "
        "of 13 to 15 cm2 V-1 s-1."
    )

    mobility = _measurements(text)[0]
    sample = next(
        condition
        for condition in mobility["condition_records"]
        if condition["field"] == "sample_form"
    )
    coverage = {item["field"]: item["status"] for item in mobility["condition_coverage"]}

    assert sample["value"] == "film"
    assert sample["raw_text"] == "films"
    assert sample["binding_scope"] == "measurement"
    assert text[sample["span"]["start"] : sample["span"]["end"]] == "films"
    assert coverage["sample_form"] == "reported"


def test_film_mention_in_another_sentence_stays_unaligned():
    fields = extract_mobility_fields(
        "Prior work used films. In this work, the mobility was 8 cm2 V-1 s-1."
    )

    assert fields is not None
    mobility = fields["mobilities"][0]
    condition_fields = {item["field"] for item in mobility.get("condition_records", [])}
    coverage = {item["field"]: item["status"] for item in mobility["condition_coverage"]}

    assert "sample_form" not in condition_fields
    assert coverage["sample_form"] == "not_aligned"
    assert "sample_form_not_aligned" in mobility["review_flags"]
    candidates = [
        item for item in fields["condition_candidates"] if item["field"] == "sample_form"
    ]
    assert len(candidates) == 1
    assert candidates[0]["value"] == "film"
    assert candidates[0]["review_flags"] == ["not_bound_to_measurement"]


def test_device_conditions_are_measurement_bound_with_normalized_source_evidence():
    text = (
        "Figure 4 shows a single-crystal field-effect transistor with a mobility "
        "of 12.3 cm2 V-1 s-1."
    )
    fields = extract_mobility_fields(text)
    assert fields is not None
    source = {
        "id": "device.pdf",
        "kind": "pdf",
        "page": 5,
        "paragraph_index": 29,
        "doi": "10.1038/example",
    }

    record = normalized_mobility_item(source, text, fields)
    mobility = record["fields"]["mobilities"][0]
    conditions = {item["field"]: item for item in mobility["condition_records"]}

    assert conditions["device_type"]["value"] == "single-crystal field-effect transistor"
    assert conditions["sample_form"]["value"] == "single crystal"
    for condition in conditions.values():
        assert condition["binding_scope"] in {"measurement", "material"}
        assert condition["review_flags"] == []
        evidence_ref = condition["evidence_refs"][0]
        assert evidence_ref["page"] == 5
        assert evidence_ref["paragraph_index"] == 29
        span = evidence_ref["span"]
        assert text[span["start"] : span["end"]] == condition["raw_text"]


def test_page_fabrication_conditions_link_through_explicit_same_device_identity():
    passage = (
        "Figure 4 shows a single-crystal field-effect transistor with a mobility "
        "of 12.3 cm2 V-1 s-1."
    )
    page_text = (
        "A laminated SC-FET used a bottom-contact, bottom-gate geometry. "
        "Au bottom contacts were deposited. The crystals were manually laminated. "
        + passage
    )
    source = {
        "id": "device.pdf",
        "kind": "pdf",
        "page": 5,
        "paragraph_index": 29,
        "doi": "10.1038/example",
    }
    record = record_from_text(passage, source)
    assert record is not None

    linked = _link_page_fabrication_conditions(page_text, [record])[0]
    mobility = linked["fields"]["mobilities"][0]
    conditions = {item["field"]: item for item in mobility["condition_records"]}
    coverage = {item["field"]: item["status"] for item in mobility["condition_coverage"]}

    assert conditions["device_geometry"]["raw_text"] == "bottom-contact, bottom-gate geometry"
    assert conditions["electrode"]["raw_text"] == "Au bottom contacts"
    assert conditions["fabrication_method"]["raw_text"] == "manually laminated"
    assert coverage["device_fabrication"] == "reported"
    assert coverage["device_geometry"] == "reported"
    assert coverage["electrode"] == "reported"
    assert coverage["fabrication_method"] == "reported"
    assert coverage["synthesis_processing"] == "not_reported"
    source_anchor_texts = set()
    for field in ("device_geometry", "electrode", "fabrication_method"):
        condition = conditions[field]
        span = condition["span"]
        assert condition["span_scope"] == "normalized_page_text"
        assert page_text[span["start"] : span["end"]] == condition["raw_text"]
        evidence_ref = condition["evidence_refs"][0]
        assert evidence_ref["page"] == 5
        assert evidence_ref["doi"] == "10.1038/example"
        relation = condition["relation_path"][0]
        assert relation["relation"] == "same_device_type"
        assert relation["source_anchor"]["value"] == "single-crystal field-effect transistor"
        source_anchor_texts.add(relation["source_anchor"]["raw_text"])
        assert relation["target_anchor"]["value"] == "single-crystal field-effect transistor"
    assert "SC-FET" in source_anchor_texts


def test_page_fabrication_conditions_do_not_cross_between_device_types():
    passage = (
        "Figure 4 shows a single-crystal field-effect transistor with a mobility "
        "of 12.3 cm2 V-1 s-1."
    )
    page_text = (
        "A thin-film transistor used a bottom-contact, bottom-gate geometry with "
        "Au bottom contacts. "
        + ("Unrelated discussion. " * 50)
        + passage
    )
    record = record_from_text(
        passage,
        {"id": "device.pdf", "kind": "pdf", "page": 5, "paragraph_index": 29},
    )
    assert record is not None

    linked = _link_page_fabrication_conditions(page_text, [record])[0]
    mobility = linked["fields"]["mobilities"][0]
    condition_fields = {item["field"] for item in mobility["condition_records"]}
    coverage = {item["field"]: item["status"] for item in mobility["condition_coverage"]}

    assert "device_geometry" not in condition_fields
    assert "electrode" not in condition_fields
    assert coverage["device_fabrication"] == "not_reported"
    assert coverage["device_geometry"] == "not_reported"
    assert coverage["electrode"] == "not_reported"


def test_prior_work_fabrication_condition_is_retained_but_not_bound():
    passage = (
        "Figure 4 shows a single-crystal field-effect transistor with a mobility "
        "of 12.3 cm2 V-1 s-1."
    )
    page_text = (
        "In prior work SC-FETs used a bottom-contact, bottom-gate geometry. "
        + passage
    )
    record = record_from_text(
        passage,
        {
            "id": "device.pdf",
            "kind": "pdf",
            "page": 5,
            "paragraph_index": 29,
            "doi": "10.1038/example",
        },
    )
    assert record is not None

    linked = _link_page_fabrication_conditions(page_text, [record])[0]
    mobility = linked["fields"]["mobilities"][0]
    condition_fields = {item["field"] for item in mobility["condition_records"]}
    coverage = {item["field"]: item["status"] for item in mobility["condition_coverage"]}

    assert "device_geometry" not in condition_fields
    assert coverage["device_geometry"] == "not_aligned"
    assert coverage["device_fabrication"] == "not_aligned"
    assert "device_geometry_prior_work_not_aligned" in mobility["review_flags"]
    candidates = [
        item
        for item in mobility["condition_candidates"]
        if item["field"] == "device_geometry"
    ]
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["source_relation"] == "prior_work"
    assert candidate["binding_scope"] == "document"
    assert candidate["review_flags"] == ["prior_work_not_bound_to_measurement"]
    assert candidate["relation_path"][0]["blocked_by"] == "source_relation"
    assert candidate["evidence_refs"][0]["page"] == 5
    cue = candidate["source_relation_evidence"][0]
    assert page_text[cue["span"]["start"] : cue["span"]["end"]] == cue["raw_text"]
    assert mobility["review_status"] == "BLOCKED"
    assert "device_geometry_prior_work_not_aligned" in mobility["review_status_reasons"]


def test_panel_boundary_blocks_saturation_bias_from_linear_mobility():
    text = (
        "The drain-source bias (VDS) was -1.0 V. (c) Transfer characteristics in the "
        "linear regime of the single-crystal field-effect transistor with a mobility "
        "of 16.0 cm2 V-1 s-1."
    )

    fields = extract_mobility_fields(text)
    assert fields is not None
    mobility = fields["mobilities"][0]
    condition_fields = {item["field"] for item in mobility["condition_records"]}
    coverage = {item["field"]: item["status"] for item in mobility["condition_coverage"]}

    assert "drain_source_voltage" not in condition_fields
    assert coverage["drain_source_voltage"] == "not_aligned"
    assert "drain_source_voltage_not_aligned" in mobility["review_flags"]
    candidates = [
        item for item in fields["condition_candidates"] if item["field"] == "drain_source_voltage"
    ]
    assert len(candidates) == 1
    assert candidates[0]["normalized_value"] == -1.0
    assert candidates[0]["normalized_unit"] == "V"
    assert candidates[0]["binding_scope"] == "document"
    assert candidates[0]["review_flags"] == ["not_bound_to_measurement"]


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


def test_post_value_for_phrase_binds_cof_material_and_current_work():
    text = (
        "Using Δσ = Nabs·ϕ·e·μ, we extract an effective mobility (ϕ·μ) of "
        "200 cm2 V-1 s-1 for PI-DY2DP, which represents a lower bound for μ."
    )

    fields = extract_mobility_fields(text)

    assert fields is not None
    assert [item["material"] for item in fields["materials"]] == ["PI-DY2DP"]
    assert fields["materials"][0]["binding_basis"] == "post_value_for_phrase"
    material_span = fields["materials"][0]["span"]
    assert text[material_span["start"] : material_span["end"]] == "PI-DY2DP"
    mobility = fields["mobilities"][0]
    assert mobility["source_relation"] == "current_work"
    assert mobility["material_refs"] == [0]
    material_condition = next(
        item for item in mobility["condition_records"] if item["field"] == "material_identity"
    )
    assert material_condition["value"] == "PI-DY2DP"
    assert material_condition["binding_scope"] == "material"
    coverage = {item["field"]: item["status"] for item in mobility["condition_coverage"]}
    assert coverage["material_identity"] == "reported"


def test_multiple_post_value_materials_remain_ambiguous_in_one_block():
    text = (
        "We extract a mobility of 10 cm2 V-1 s-1 for MatA, whereas we extract "
        "a mobility of 20 cm2 V-1 s-1 for MatB."
    )

    fields = extract_mobility_fields(text)

    assert fields is not None
    assert [item["material"] for item in fields["materials"]] == ["MatA", "MatB"]
    for mobility in fields["mobilities"]:
        assert "material_refs" not in mobility
        assert "multiple_materials_unaligned" in mobility["review_flags"]
        coverage = {
            item["field"]: item["status"] for item in mobility["condition_coverage"]
        }
        assert coverage["material_identity"] == "ambiguous"


def test_mof_caption_binds_associated_material_and_pdf_artifact_algorithm():
    text = (
        "Fig. 3 Plot of the electron mobility for a range of compositions "
        "Themobilityfollowsasimilartrendas"
        "thescattering(deformation)potentialprovidedin Figure2b."
        "ThehighestmobilityisassociatedwithUiO-66(Hf5Zr1)-BDCwithanapproximate "
        "valueof1.4x10-3 cm2/V-s."
    )

    fields = extract_mobility_fields(text)

    assert fields is not None
    assert [item["material"] for item in fields["materials"]] == [
        "UiO-66(Hf5Zr1)-BDC"
    ]
    material = fields["materials"][0]
    assert text[material["span"]["start"] : material["span"]["end"]] == material["raw_text"]
    mobility = fields["mobilities"][0]
    assert mobility["value"] == 0.0014
    assert mobility["determination"] == "computational"
    assert mobility["algorithms"] == ["deformation-potential theory"]
    assert mobility["algorithm_evidence"][0]["raw_text"] == "deformation)potential"
    assert mobility["material_refs"] == [0]
    material_condition = next(
        item for item in mobility["condition_records"] if item["field"] == "material_identity"
    )
    assert material_condition["value"] == "UiO-66(Hf5Zr1)-BDC"
    coverage = {item["field"]: item["status"] for item in mobility["condition_coverage"]}
    assert coverage["material_identity"] == "reported"


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
