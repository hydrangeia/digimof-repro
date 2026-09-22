import json
from pathlib import Path


FIXTURE = Path(__file__).parent / "fixtures" / "mobility_gold_cases.json"


def test_stratified_gold_manifest_is_complete_and_explicit_about_blockers():
    manifest = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = manifest["cases"]

    assert {case["family"] for case in cases} == {"COF", "MOF", "OSM", "PVSK"}
    assert len(cases) == 4
    for case in cases:
        assert case["status"] in {"PARTIAL_PASS", "BLOCKED"}
        assert case["source"]["relative_path"].endswith(".pdf")
        assert case["source"]["pages"]
        assert case["measurements"]
        assert case["known_parser_gaps"]
        assert case["must_not_link"]
        for measurement in case["measurements"]:
            assert measurement["material_ref"]
            assert measurement["standard_units"] == "cm^2 V^-1 s^-1"
            assert measurement["source_relation"] in {"current_work", "prior_work", "unspecified"}
            assert "value" in measurement or "value_range" in measurement
