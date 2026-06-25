from pathlib import Path

from framework_miner.report import field_values, render_html_report, summarize_records, write_html_report


def sample_record():
    return {
        "schema_version": "framework_miner/0.2",
        "framework_type": "COF",
        "source": {"id": "paper.pdf", "kind": "pdf", "paragraph_index": 4},
        "fields": {
            "names": ["TFPT-COF"],
            "polymerization_routes": [{"route": "hydrazone formation"}],
            "monomers": [
                {"monomer": "TFPT", "role": "addition"},
                {"monomer": "DETH", "role": "addition"},
            ],
            "solvents": [{"solvent": "mesitylene"}, {"solvent": "dioxane"}],
            "temperature": ["120 °C"],
            "time": ["72 h"],
        },
        "evidence_text": "TFPT-COF was synthesized at 120 °C for 72 h.",
        "passes_framework_filter": True,
    }


def test_field_values_include_roles_for_monomers():
    values = field_values(sample_record()["fields"], "monomers")

    assert values == ["TFPT (addition)", "DETH (addition)"]


def test_summarize_records_counts_frameworks_and_condition_records():
    records = [
        sample_record(),
        {
            "framework_type": "MOF",
            "source": {"id": "mof.html"},
            "fields": {"names": ["HKUST-1"]},
        },
    ]

    summary = summarize_records(records)

    assert summary["total"] == 2
    assert summary["framework_counts"] == {"COF": 1, "MOF": 1}
    assert summary["source_count"] == 2
    assert summary["named_count"] == 2
    assert summary["condition_count"] == 1


def test_render_html_report_escapes_record_text():
    record = sample_record()
    record["fields"]["names"] = ["<danger>"]
    record["evidence_text"] = "Synthesis text with <danger> markup."

    html = render_html_report([record])

    assert "&lt;danger&gt;" in html
    assert "<danger>" not in html
    assert "Framework Miner Review Report" in html


def test_write_html_report_creates_parent_directory(tmp_path: Path):
    output = tmp_path / "nested" / "report.html"

    write_html_report([sample_record()], output, jsonl_path=Path("results.jsonl"))

    html = output.read_text(encoding="utf-8")
    assert "results.jsonl" in html
    assert "TFPT-COF" in html
