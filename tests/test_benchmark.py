from pathlib import Path

from evaluate_framework_miner import load_cases, normalize_field_value, score_case


def test_gold_benchmark_cases_pass():
    cases = load_cases(Path("benchmark/gold_cases.jsonl"))
    results = [score_case(case) for case in cases]

    assert all(result["passed"] for result in results)
    assert sum(result["matched"] for result in results) == sum(result["expected"] for result in results)


def test_gold_benchmark_has_no_cjk_mojibake():
    text = Path("benchmark/gold_cases.jsonl").read_text(encoding="utf-8")
    cjk_characters = sorted({char for char in text if "\u4e00" <= char <= "\u9fff"})

    assert not cjk_characters


def test_temperature_normalization_handles_celsius_variants():
    assert normalize_field_value("temperature", "90 掳C") == "90 °C"
    assert normalize_field_value("temperature", "90 ▲C") == "90 °C"
    assert normalize_field_value("temperature", "90 \u93ba\u77ef") == "90 °C"
    assert normalize_field_value("temperature", "90 ℃") == "90 °C"
