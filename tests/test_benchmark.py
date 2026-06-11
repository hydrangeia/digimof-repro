from pathlib import Path

from evaluate_framework_miner import load_cases, score_case


def test_gold_benchmark_cases_pass():
    cases = load_cases(Path("benchmark/gold_cases.jsonl"))
    results = [score_case(case) for case in cases]

    assert all(result["passed"] for result in results)
    assert sum(result["matched"] for result in results) == sum(result["expected"] for result in results)
