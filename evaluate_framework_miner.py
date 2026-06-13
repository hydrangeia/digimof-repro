"""Evaluate framework_miner on small precision-focused gold cases."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

from framework_miner.bootstrap import ensure_repo_environment
from framework_miner.cof import CLEANSIUS_VARIANT_PATTERN
from framework_miner.legacy_digimof import merge_items, parse_html_text

ensure_repo_environment()


FIELD_VALUE_KEYS = {
    "synthesis_routes": "synthesis",
    "topologies": "abrv",
    "linker_routes": "linker",
    "polymerization_routes": "route",
    "linkages": "linkage",
    "monomers": "monomer",
    "catalysts": "catalyst",
    "bases": "base",
    "solvents": "solvent",
    "atmospheres": "atmosphere",
    "interfaces": "interface",
    "substrates": "substrate",
}


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON on line {} of {}".format(line_number, path)) from exc
    return cases


def normalize_field_value(field_name: str, value: str) -> str:
    value = " ".join(value.split())
    if field_name != "temperature":
        return value

    lower = value.lower()
    if lower in {"room temperature", "ambient temperature", "rt", "at rt"}:
        return lower[3:] if lower.startswith("at ") else lower

    match = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*K", value, flags=re.I)
    if match:
        return "{} K".format(match.group(1))

    match = re.fullmatch(
        r"(-?\d+(?:\.\d+)?)\s*(?:{}|[^0-9Kk\s]+C)".format(CLEANSIUS_VARIANT_PATTERN),
        value,
        flags=re.I,
    )
    if match:
        return "{} °C".format(match.group(1))

    return value


def values_for_field(fields: dict[str, Any], field_name: str) -> list[str]:
    values = fields.get(field_name, [])
    if not isinstance(values, list):
        return []

    value_key = FIELD_VALUE_KEYS.get(field_name)
    extracted = []
    for value in values:
        if isinstance(value, str):
            extracted.append(normalize_field_value(field_name, value))
        elif isinstance(value, dict) and value_key and isinstance(value.get(value_key), str):
            extracted.append(normalize_field_value(field_name, value[value_key]))
    return extracted


def record_passes(record: dict[str, Any], framework: str) -> bool:
    if framework == "mof":
        return bool(record.get("passes_mof_filter"))
    if framework == "cof":
        return bool(record.get("passes_framework_filter"))
    return bool(record.get("passes_mof_filter") or record.get("passes_framework_filter"))


def extract_case_records(case: dict[str, Any]) -> list[dict[str, Any]]:
    framework = case["framework"]
    escaped = html.escape(case["text"])
    content = "<html><body><p>{}</p></body></html>".format(escaped).encode("utf-8")
    records = list(merge_items(parse_html_text(content, "benchmark://{}".format(case["id"]), framework=framework)))
    return [record for record in records if record_passes(record, framework)]


def score_case(case: dict[str, Any]) -> dict[str, Any]:
    records = extract_case_records(case)
    expected = case.get("expected", {})
    actual_by_field: dict[str, list[str]] = {}
    for record in records:
        fields = record.get("fields", {})
        for field_name in expected:
            actual_by_field.setdefault(field_name, [])
            for value in values_for_field(fields, field_name):
                if value not in actual_by_field[field_name]:
                    actual_by_field[field_name].append(value)

    missing: dict[str, list[str]] = {}
    for field_name, expected_values in expected.items():
        expected_values = [normalize_field_value(field_name, value) for value in expected_values]
        actual_values = actual_by_field.get(field_name, [])
        field_missing = [value for value in expected_values if value not in actual_values]
        if field_missing:
            missing[field_name] = field_missing

    expected_count = sum(len(values) for values in expected.values())
    missing_count = sum(len(values) for values in missing.values())
    matched_count = expected_count - missing_count
    return {
        "id": case["id"],
        "framework": case["framework"],
        "passed": not missing,
        "matched": matched_count,
        "expected": expected_count,
        "missing": missing,
        "actual": actual_by_field,
        "record_count": len(records),
    }


def write_markdown(results: list[dict[str, Any]], output: Path) -> None:
    passed = sum(1 for result in results if result["passed"])
    total = len(results)
    lines = [
        "# Framework Miner Benchmark",
        "",
        "- Cases: {}".format(total),
        "- Passed: {}".format(passed),
        "- Field recall: {}/{}".format(
            sum(result["matched"] for result in results),
            sum(result["expected"] for result in results),
        ),
        "",
        "| Case | Framework | Status | Matched | Missing |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        missing = json.dumps(result["missing"], ensure_ascii=False) if result["missing"] else ""
        lines.append(
            "| {id} | {framework} | {status} | {matched}/{expected} | {missing} |".format(
                id=result["id"],
                framework=result["framework"].upper(),
                status=status,
                matched=result["matched"],
                expected=result["expected"],
                missing=missing,
            )
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate framework_miner on gold synthesis cases.")
    parser.add_argument("--cases", type=Path, default=Path("benchmark/gold_cases.jsonl"))
    parser.add_argument("--json-output", type=Path, default=Path("benchmark/results.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("benchmark/results.md"))
    args = parser.parse_args()

    cases = load_cases(args.cases)
    results = [score_case(case) for case in cases]
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(results, args.markdown_output)

    passed = sum(1 for result in results if result["passed"])
    total = len(results)
    matched = sum(result["matched"] for result in results)
    expected = sum(result["expected"] for result in results)
    print("cases: {}/{} passed".format(passed, total))
    print("field recall: {}/{}".format(matched, expected))
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
