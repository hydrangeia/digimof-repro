"""Lightweight COF extraction heuristics for framework_miner."""

from __future__ import annotations

import re
from typing import Iterable


COF_PARAGRAPH_TERMS = [
    "cof",
    "covalent organic framework",
    "covalent-organic framework",
    "suzuki",
    "schiff",
    "knoevenagel",
    "boronate ester",
    "imine",
]

COF_ROUTE_TERMS = [
    "Suzuki polymerization",
    "Suzuki coupling",
    "Schiff base polycondensation",
    "Schiff-base polycondensation",
    "Knoevenagel condensation",
    "boronate ester condensation",
    "solvothermal",
    "ionothermal",
    "mechanochemical",
    "sonochemical",
    "vapor induced conversion",
    "liquid-liquid interface",
    "liquid/liquid interface",
    "on-water surface",
]

COF_LINKAGE_TERMS = [
    "C-C bonded",
    "C-C bond",
    "sp2-carbon-linked",
    "sp2 carbon-linked",
    "sp2c",
    "imine-linked",
    "hydrazone-linked",
    "boronate ester",
    "beta-ketoenamine",
    "β-ketoenamine",
    "triazine",
]

COF_INTERFACE_TERMS = [
    "liquid-liquid interface",
    "liquid/liquid interface",
    "air-water interface",
    "air/water interface",
    "on-water surface",
    "water/toluene interface",
]

COF_CATALYST_TERMS = [
    "Pd(PPh3)4",
    "tetrakis(triphenylphosphine)palladium",
    "Pd(OAc)2",
    "Sc(OTf)3",
    "p-toluenesulfonic acid",
    "acetic acid",
]

COF_BASE_TERMS = [
    "K2CO3",
    "Na2CO3",
    "Cs2CO3",
    "triethylamine",
    "DIPEA",
]

COF_SOLVENT_TERMS = [
    "toluene",
    "water",
    "ethanol",
    "methanol",
    "mesitylene",
    "dioxane",
    "1,4-dioxane",
    "n-butanol",
    "o-dichlorobenzene",
    "DMF",
    "DMAc",
    "chloroform",
]

COF_NAME_PATTERNS = [
    r"\b(?:[A-Za-z0-9]+[-_]){1,5}COF[A-Za-z0-9-]*\b",
    r"\b[A-Za-z0-9]*COF[A-Za-z0-9-]*\b",
    r"\bCOF-\d+[A-Za-z0-9-]*\b",
    r"\b2DCCOF\d+\b",
    r"\b3DCCOF\d+\b",
]


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _find_terms(text: str, terms: Iterable[str]) -> list[str]:
    lower = text.lower()
    found: list[str] = []
    for term in sorted(terms, key=len, reverse=True):
        if term.lower() in lower:
            _append_unique(found, term)

    compact: list[str] = []
    for term in found:
        term_lower = term.lower()
        if any(term_lower != other.lower() and term_lower in other.lower() for other in found):
            continue
        compact.append(term)
    return compact


def is_cof_candidate_text(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in COF_PARAGRAPH_TERMS)


def clean_cof_name(name: str) -> str:
    name = " ".join(name.split())
    return name.strip(" \t\r\n,.;:()[]")


def heuristic_cof_names(text: str) -> list[str]:
    names: list[str] = []
    for pattern in COF_NAME_PATTERNS:
        for match in re.finditer(pattern, text):
            name = clean_cof_name(match.group(0))
            if name.lower() not in {"cof", "cofs"}:
                _append_unique(names, name)

    for match in re.finditer(
        r"covalent\s+organic\s+framework\s*\(COF\),\s*([^.;]+?)(?=,\s*(?:was|were|which|that|with)\b|;|\.|$)",
        text,
        flags=re.I,
    ):
        _append_unique(names, clean_cof_name(match.group(1)))
    return names


def _temperature_values(text: str) -> list[str]:
    return [
        " ".join(match.group(0).split())
        for match in re.finditer(r"\b-?\d+(?:\.\d+)?\s*(?:°C|℃|K)\b", text)
    ]


def _time_values(text: str) -> list[str]:
    return [
        " ".join(match.group(0).split())
        for match in re.finditer(
            r"\b\d+(?:\.\d+)?\s*(?:min|minutes?|h|hours?|d|days?|months?)\b|\bone month\b",
            text,
            flags=re.I,
        )
    ]


def heuristic_cof_fields(text: str) -> dict | None:
    if not is_cof_candidate_text(text):
        return None

    names = heuristic_cof_names(text)
    fields: dict = {}
    if names:
        fields["names"] = names

    routes = _find_terms(text, COF_ROUTE_TERMS)
    if routes:
        fields["polymerization_routes"] = [{"route": route} for route in routes]

    linkages = _find_terms(text, COF_LINKAGE_TERMS)
    if linkages:
        fields["linkages"] = [{"linkage": linkage} for linkage in linkages]

    catalysts = _find_terms(text, COF_CATALYST_TERMS)
    if catalysts:
        fields["catalysts"] = [{"catalyst": catalyst} for catalyst in catalysts]

    bases = _find_terms(text, COF_BASE_TERMS)
    if bases:
        fields["bases"] = [{"base": base} for base in bases]

    solvents = _find_terms(text, COF_SOLVENT_TERMS)
    if solvents:
        fields["solvents"] = [{"solvent": solvent} for solvent in solvents]

    interfaces = _find_terms(text, COF_INTERFACE_TERMS)
    if interfaces:
        fields["interfaces"] = [{"interface": interface} for interface in interfaces]

    temperatures = _temperature_values(text)
    if temperatures:
        fields["temperature"] = temperatures

    times = _time_values(text)
    if times:
        fields["time"] = times

    if not fields or "names" not in fields:
        return None
    return fields


def normalized_cof_item(source: dict, evidence_text: str, fields: dict) -> dict:
    return {
        "schema_version": "framework_miner/0.2",
        "framework_type": "COF",
        "source": source,
        "evidence_text": evidence_text,
        "fields": fields,
        "passes_framework_filter": True,
        "extraction_method": "cof_paragraph_heuristic",
    }
