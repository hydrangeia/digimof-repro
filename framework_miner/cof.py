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
    "hydrazone",
    "beta-ketoenamine",
    "\u03b2-ketoenamine",
    "olefin",
    "vinylene",
]

COF_ROUTE_TERMS = [
    "Suzuki polymerization",
    "Suzuki coupling",
    "azomethine coupling",
    "Schiff base reaction",
    "Schiff-base reaction",
    "Schiff base chemical reaction",
    "Schiff-base chemical reaction",
    "Schiff base condensation",
    "Schiff base polycondensation",
    "Schiff-base condensation",
    "Schiff-base polycondensation",
    "Knoevenagel condensation",
    "Knoevenagel polycondensation",
    "boronate ester condensation",
    "boronic acid condensation",
    "hydrazone formation",
    "hydrazone condensation",
    "solvothermal",
    "ionothermal",
    "mechanochemical",
    "sonochemical",
    "vapor induced conversion",
    "liquid-liquid interface",
    "liquid/liquid interface",
    "on-water surface",
    "transesterification reaction",
]

COF_ROUTE_ALIASES = [
    (r"\bvapou?r[\s-]+induced\s+conversion\b", "vapor induced conversion"),
    (r"\bVIC\b", "vapor induced conversion"),
    (r"\bUllmann(?:-like)?(?:\s+on-surface)?\s+(?:reaction|coupling)\b", "Ullmann coupling"),
]

COF_LINKAGE_TERMS = [
    "C-C bonded",
    "C-C bond",
    "sp2-carbon-linked",
    "sp2 carbon-linked",
    "sp2c",
    "imine-linked",
    "imine-based",
    "hydrazone-linked",
    "olefin-linked",
    "vinylene-linked",
    "boronate ester",
    "boroxine",
    "beta-ketoenamine-linked",
    "beta-ketoenamine",
    "\u03b2-ketoenamine-linked",
    "\u03b2-ketoenamine",
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

COF_INTERFACE_ALIASES = [
    (r"\bliquid/liquid\s+interface\b", "liquid-liquid interface"),
    (r"\bair/water\s+interface\b", "air-water interface"),
]

COF_SUBSTRATE_TERMS = [
    "ITO glass",
    "indium tin oxide glass",
    "FTO glass",
    "fluorine-doped tin oxide glass",
    "Au(111)",
    "glass substrate",
    "quartz substrate",
    "silicon wafer",
    "copper foil",
    "nickel foam",
    "carbon cloth",
]

COF_SUBSTRATE_ALIASES = [
    (r"indium\s+tin\s+oxide(?:\s*\(ITO\))?(?:\s+glass|\s+substrate)?", "ITO glass"),
    (r"ITO(?:\s+glass|\s+substrate)?", "ITO glass"),
    (r"fluorine[\s-]+doped\s+tin\s+oxide(?:\s*\(FTO\))?(?:\s+glass|\s+substrate)?", "FTO glass"),
    (r"FTO(?:\s+glass|\s+substrate)?", "FTO glass"),
    (r"(?:[A-Za-z-]+\s+){0,3}Au\(111\)(?:\s+surface)?", "Au(111)"),
]

COF_CATALYST_TERMS = [
    "Pd(PPh3)4",
    "tetrakis(triphenylphosphine)palladium",
    "Pd(OAc)2",
    "Sc(OTf)3",
    "p-toluenesulfonic acid",
    "acetic acid",
    "trifluoroacetic acid",
]

COF_CATALYST_ALIASES = [
    (r"\b(?:AcOH|HOAc)\b", "acetic acid"),
    (r"\bTFA\b", "trifluoroacetic acid"),
    (r"\b(?:p-?TsOH|PTSA)\b", "p-toluenesulfonic acid"),
]

COF_BASE_TERMS = [
    "K2CO3",
    "Na2CO3",
    "Cs2CO3",
    "triethylamine",
    "diisopropylethylamine",
    "DIPEA",
    "piperidine",
]

COF_BASE_ALIASES = [
    (r"\b(?:Et3N|NEt3|TEA)\b", "triethylamine"),
    (r"\bH[u\u00fc]nig'?s?\s+base\b", "DIPEA"),
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
    "1,2-dichlorobenzene",
    "o-DCB",
    "DMF",
    "DMAc",
    "THF",
    "acetonitrile",
    "chloroform",
    "dichloromethane",
    "DCM",
]

COF_SOLVENT_ALIASES = [
    (r"\baqueous(?:\s+\w+){0,2}\s+solution\b", "water"),
    (r"\bMeCN\b", "acetonitrile"),
    (r"\bCH3CN\b", "acetonitrile"),
    (r"\bMeOH\b", "methanol"),
    (r"\bEtOH\b", "ethanol"),
    (r"\bo-?DCB\b", "1,2-dichlorobenzene"),
    (r"\bn-?BuOH\b", "n-butanol"),
    (r"\b(?:DCM|CH2Cl2)\b", "dichloromethane"),
    (r"\btetrahydrofuran\b", "THF"),
    (r"\bN,N-dimethylformamide\b", "DMF"),
    (r"\bN,N-dimethylacetamide\b", "DMAc"),
]

COF_ATMOSPHERE_TERMS = [
    "argon",
    "hydrogen",
    "nitrogen",
    "air",
    "vacuum",
    "inert atmosphere",
]

COF_NAME_PATTERNS = [
    r"\b[A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9]+){1,4}\s+COF\b",
    r"\b(?:[A-Za-z0-9]+[-_]){1,5}COF[A-Za-z0-9-]*\b",
    r"(?<![A-Za-z0-9-])\b[A-Za-z0-9]*COF[A-Za-z0-9-]*\b",
    r"(?<![A-Za-z0-9-])\bCOF-\d+[A-Za-z0-9-]*\b",
    r"\b2DCCOF\d+\b",
    r"\b3DCCOF\d+\b",
]

TEMPERATURE_UNIT_VARIANTS = (
    "\u00b0\\s*C",
    "\u00ba\\s*C",
    "\u2103",
    "\u63b3C",
    "\u93ba\u77ef",
    "\u0431\u0443C",
    "\u0431\u0446",
    "\u9229\u5104K",
)

MONOMER_STOP_WORDS = {
    "argon",
    "nitrogen",
    "vacuum",
    "investigated",
    "characterized",
    "studied",
    "examined",
    "analyzed",
    "probed",
    "water",
    "toluene",
    "ethanol",
    "methanol",
    "mesitylene",
    "dioxane",
    "1,4-dioxane",
    "K2CO3",
    "Pd(PPh3)4",
}
MONOMER_STOP_WORDS_LOWER = {word.lower() for word in MONOMER_STOP_WORDS}
TEMPERATURE_UNIT_PATTERN = "(?:{})".format("|".join(TEMPERATURE_UNIT_VARIANTS))
CLEANSIUS_VARIANT_PATTERN = "(?:{})".format("|".join(TEMPERATURE_UNIT_VARIANTS[:-1]))
ATMOSPHERE_LABEL_PATTERN = r"argon|hydrogen|nitrogen|air|vacuum|Ar|H2|H₂|N2|N₂"
AUXILIARY_COMPONENT_PATTERN = r"powders?|precursors?|monomers?|ligands?|dialdehydes?|amines?"
WORKUP_TERM_PATTERN = (
    r"centrifug(?:ed|ation)?|wash(?:ed|ing)?|filter(?:ed|ing)?|dried?|"
    r"transferred|storage vial|characterized|opened|precipitate"
)


def _normalize_atmosphere_value(value: str) -> str:
    normalized = value.strip().lower()
    return {
        "ar": "argon",
        "h2": "hydrogen",
        "h₂": "hydrogen",
        "n2": "nitrogen",
        "n₂": "nitrogen",
    }.get(normalized, normalized)


def _normalize_substrate_value(value: str) -> str:
    normalized = " ".join(value.split())
    return {
        "indium tin oxide glass": "ITO glass",
        "indium tin oxide substrate": "ITO glass",
        "indium tin oxide (ito)": "ITO glass",
        "indium tin oxide (ito) substrate": "ITO glass",
        "ito": "ITO glass",
        "ito substrate": "ITO glass",
        "fluorine-doped tin oxide glass": "FTO glass",
        "fluorine-doped tin oxide substrate": "FTO glass",
        "fluorine-doped tin oxide (fto)": "FTO glass",
        "fluorine-doped tin oxide (fto) substrate": "FTO glass",
        "fto": "FTO glass",
        "fto substrate": "FTO glass",
    }.get(normalized.lower(), normalized)


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _catalyst_values(text: str) -> list[str]:
    values = _find_terms(text, COF_CATALYST_TERMS)
    for pattern, normalized in COF_CATALYST_ALIASES:
        for _match in re.finditer(pattern, text, flags=re.I):
            _append_unique(values, normalized)
    return values


def _base_values(text: str) -> list[str]:
    values = _find_terms(text, COF_BASE_TERMS)
    for pattern, normalized in COF_BASE_ALIASES:
        for _match in re.finditer(pattern, text, flags=re.I):
            _append_unique(values, normalized)
    return values


def _sentence_bounds(text: str, position: int) -> tuple[int, int]:
    start = max(text.rfind(marker, 0, position) for marker in ".;!?")
    end_candidates = [index for marker in ".;!?" if (index := text.find(marker, position)) != -1]
    end = min(end_candidates) if end_candidates else len(text)
    return start + 1, end


def _sentence_contains_workup_terms(text: str, position: int) -> bool:
    sentence_start, sentence_end = _sentence_bounds(text, position)
    sentence = text[sentence_start:sentence_end]
    return bool(re.search(r"\b(?:{})\b".format(WORKUP_TERM_PATTERN), sentence, flags=re.I))


def _solvent_values(text: str) -> list[str]:
    normalized_values: list[str] = []
    for value in _find_terms(text, COF_SOLVENT_TERMS):
        canonical = {
            "o-dichlorobenzene": "1,2-dichlorobenzene",
            "o-DCB": "1,2-dichlorobenzene",
            "DCM": "dichloromethane",
        }.get(value, value)
        for match in re.finditer(re.escape(value), text, flags=re.I):
            if _sentence_contains_workup_terms(text, match.start()):
                continue
            _append_unique(normalized_values, canonical)
            break
    for pattern, normalized in COF_SOLVENT_ALIASES:
        for match in re.finditer(pattern, text, flags=re.I):
            if _sentence_contains_workup_terms(text, match.start()):
                continue
            _append_unique(normalized_values, normalized)
    return normalized_values


def _route_values(text: str) -> list[str]:
    values = _find_terms(text, COF_ROUTE_TERMS)
    for pattern, normalized in COF_ROUTE_ALIASES:
        for _match in re.finditer(pattern, text, flags=re.I):
            _append_unique(values, normalized)
    return values


def _linkage_values(text: str) -> list[str]:
    values = _find_terms(text, COF_LINKAGE_TERMS)
    normalized_values: list[str] = []
    for value in values:
        canonical = {
            "imine-based": "imine",
        }.get(value, value)
        _append_unique(normalized_values, canonical)
    return normalized_values


def _interface_values(text: str) -> list[str]:
    values = _find_terms(text, COF_INTERFACE_TERMS)
    normalized_values: list[str] = []
    for value in values:
        canonical = {
            "liquid/liquid interface": "liquid-liquid interface",
            "air/water interface": "air-water interface",
        }.get(value, value)
        _append_unique(normalized_values, canonical)
    for pattern, normalized in COF_INTERFACE_ALIASES:
        for _match in re.finditer(pattern, text, flags=re.I):
            _append_unique(normalized_values, normalized)
    return normalized_values


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
    name = name.strip(" \t\r\n,.;:")
    if (name.startswith("(") and name.endswith(")")) or (name.startswith("[") and name.endswith("]")):
        name = name[1:-1].strip()
    return name


def _looks_like_cof_name(name: str) -> bool:
    cleaned = clean_cof_name(name)
    if not cleaned:
        return False
    if cleaned.lower() in {"cof", "cofs"}:
        return False

    residual = re.sub(r"\bCOFs?\b", " ", cleaned, flags=re.I)
    residual = " ".join(residual.split()).strip(" -")
    if not residual:
        return False
    if re.match(r"^(?:we|here|this|these|those|a|an|the)\b", residual, flags=re.I):
        return False
    return bool(re.search(r"[A-Z0-9]", residual))


def clean_monomer_name(name: str) -> str:
    name = re.sub(r"^\s*(?:the|a|an)\b\s*", "", name, flags=re.I)
    name = re.sub(r"\s+", " ", name)
    name = name.strip(" \t\r\n,.;:")
    name = re.sub(r"\(([A-Za-z0-9-]+),\s*\d+%\)", r"(\1)", name)
    name = re.sub(r"\s*\(\d+\)\s*$", "", name)
    if (name.startswith("(") and name.endswith(")")) or (name.startswith("[") and name.endswith("]")):
        name = name[1:-1].strip()
    return name


def heuristic_cof_names(text: str) -> list[str]:
    names: list[str] = []

    for match in re.finditer(
        r"\b([A-Z][A-Za-z0-9]+(?:-[A-Za-z0-9]+)+(?:\s*,\s*(?:and\s+)?[A-Z][A-Za-z0-9]+(?:-[A-Za-z0-9]+)+)+)"
        r"\s+COFs?\s+(?:films?|powders?|nanosheets?|frameworks?)\b",
        text,
        flags=re.I,
    ):
        for raw_name in re.split(r"\s*,\s*(?:and\s+)?", match.group(1)):
            name = clean_cof_name(raw_name + " COF")
            if _looks_like_cof_name(name):
                _append_unique(names, name)

    for match in re.finditer(
        r"\bCOF\s+([A-Z][A-Za-z0-9]+(?:-[A-Za-z0-9]+){1,4})(?=-graphene\b|\s+(?:graphene|powder|film)\b)",
        text,
    ):
        name = clean_cof_name("COF" + match.group(1))
        if _looks_like_cof_name(name):
            _append_unique(names, name)



    for pattern in COF_NAME_PATTERNS:
        for match in re.finditer(pattern, text):
            name = clean_cof_name(match.group(0))
            if _looks_like_cof_name(name):
                _append_unique(names, name)

    for match in re.finditer(
        r"covalent\s+organic\s+framework\s*\(COF\),\s*([^.;]+?)(?=,\s*(?:was|were|which|that|with)\b|;|\.|$)",
        text,
        flags=re.I,
    ):
        name = clean_cof_name(match.group(1))
        if _looks_like_cof_name(name):
            _append_unique(names, name)
    for match in re.finditer(
        r"\b(?:[A-Za-z-]+linked\s+)?COFs?,\s*([^.;]+?)(?=,\s*(?:was|were|is|are|all|which|that|with)\b|;|\.|$)",
        text,
        flags=re.I,
    ):
        name = clean_cof_name(match.group(1))
        if _looks_like_cof_name(name):
            _append_unique(names, name)
    return names


def _is_auxiliary_component_temperature(text: str, start: int) -> bool:
    sentence_start, sentence_end = _sentence_bounds(text, start)
    sentence = text[sentence_start:sentence_end]
    relative_start = start - sentence_start
    pattern = (
        r"\btemperature\s+of\s+(?:the\s+)?[^.;!?]{{0,120}}?\b(?:{})\b"
        r"[^.;!?]{{0,80}}?\b(?:controlled|maintained|kept|held)\s+at\b"
    ).format(AUXILIARY_COMPONENT_PATTERN)
    for match in re.finditer(pattern, sentence, flags=re.I):
        auxiliary_end = len(sentence)
        when_match = re.search(r"\bwhen\b", sentence[match.end():], flags=re.I)
        if when_match:
            auxiliary_end = match.end() + when_match.start()
        if match.end() <= relative_start < auxiliary_end:
            return True
    return False


def _temperature_values(text: str) -> list[str]:
    values: list[str] = []
    pattern = r"\b-?\d+(?:\.\d+)?\s*{}(?=\s|[),.;:]|$)".format(TEMPERATURE_UNIT_PATTERN)
    for match in re.finditer(pattern, text):
        if _is_auxiliary_component_temperature(text, match.start()):
            continue
        normalized = " ".join(match.group(0).split())
        normalized = re.sub(r"\s*{}\Z".format(CLEANSIUS_VARIANT_PATTERN), " °C", normalized)
        _append_unique(values, normalized)
    for match in re.finditer(r"\b(?:room|ambient)[-\s]+temperature\b|\bat\s+RT\b|\bRT\b", text, flags=re.I):
        if _sentence_contains_workup_terms(text, match.start()):
            continue
        value = re.sub(r"^at\s+", "", " ".join(match.group(0).split()), flags=re.I)
        value = re.sub(r"[-\s]+", " ", value)
        _append_unique(values, value)
    return values


def _time_values(text: str) -> list[str]:
    values: list[str] = []
    number_words = "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
    pattern = (
        r"\b(?:\d+(?:\.\d+)?|{})\s*(?:-\s*)?"
        r"(?:min|minutes?|h|hours?|days?|weeks?|months?)\b|\bovernight\b"
    ).format(number_words)
    for match in re.finditer(pattern, text, flags=re.I):
        if _sentence_contains_workup_terms(text, match.start()):
            continue
        sentence_start, sentence_end = _sentence_bounds(text, match.start())
        if re.search(r"\bsonicat(?:ed|ion)\b", text[sentence_start:sentence_end], flags=re.I):
            continue
        _append_unique(values, " ".join(match.group(0).split()))
    return values


def _atmosphere_values(text: str) -> list[str]:
    values: list[str] = []
    atmosphere_label_group = r"(?:{})".format(ATMOSPHERE_LABEL_PATTERN)
    patterns = [
        r"\bunder\s+(?:an?\s+)?(?:inert\s+)?(?P<atmosphere>{})\b".format(ATMOSPHERE_LABEL_PATTERN),
        r"\bunder\s+(?:an?\s+)?(?P<atmosphere>{})\s+atmosphere\b".format(ATMOSPHERE_LABEL_PATTERN),
        r"\bunder\s+(?:an?\s+)?(?:flow|stream)\s+of\s+(?P<atmosphere>{})\b".format(ATMOSPHERE_LABEL_PATTERN),
        r"\bunder\s+(?:an?\s+)?(?P<atmosphere>{})\s+(?:flow|stream)\b".format(ATMOSPHERE_LABEL_PATTERN),
        r"\bunder\s+flowing\s+(?P<atmosphere>{})\b".format(ATMOSPHERE_LABEL_PATTERN),
        r"\b(?:under|in)\s+(?:an?\s+)?atmosphere\s+of\s+(?P<atmosphere>{})\b".format(ATMOSPHERE_LABEL_PATTERN),
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.I):
            _append_unique(values, _normalize_atmosphere_value(match.group("atmosphere")))
    carrier_gas_patterns = [
        r"\b(?P<series>{label}(?:\s*(?:,|/|and)\s*{label})+)\s+flow\b[^.;]{{0,120}}\bcarrier gas\b".format(
            label=atmosphere_label_group
        ),
        r"\bflow\s+of\s+(?P<series>{label}(?:\s*(?:,|/|and)\s*{label})+)\b[^.;]{{0,120}}\bcarrier gas\b".format(
            label=atmosphere_label_group
        ),
    ]
    for pattern in carrier_gas_patterns:
        for match in re.finditer(pattern, text, flags=re.I):
            for atmosphere in re.findall(ATMOSPHERE_LABEL_PATTERN, match.group("series"), flags=re.I):
                _append_unique(values, _normalize_atmosphere_value(atmosphere))
    for match in re.finditer(r"\bunder\s+(?:an?\s+)?inert\s+atmosphere\b", text, flags=re.I):
        _append_unique(values, "inert atmosphere")
    return values


def _substrate_values(text: str) -> list[str]:
    values: list[str] = []
    substrate_alias_pattern = "|".join(
        "(?P<alias_{}>{})".format(index, pattern)
        for index, (pattern, _normalized) in enumerate(COF_SUBSTRATE_ALIASES)
    )
    substrate_pattern = "|".join(re.escape(term) for term in sorted(COF_SUBSTRATE_TERMS, key=len, reverse=True))
    substrate_end = r"(?=[\s,.;)]|$)"
    patterns = [
        r"\b(?:grown|deposited|prepared|synthesized|formed|cast|coated)\s+(?:on|onto)\s+(?P<substrate>{}){}".format(
            substrate_pattern, substrate_end
        ),
        r"\b(?:grown|deposited|prepared|synthesized|formed|cast|coated)\s+(?:on|onto)\s+{}{}".format(
            substrate_alias_pattern, substrate_end
        ),
        r"\bsupported\s+on\s+(?P<substrate>{}){}".format(substrate_pattern, substrate_end),
        r"\bsupported\s+on\s+{}{}".format(substrate_alias_pattern, substrate_end),
        r"\b(?:on|onto)\s+(?P<substrate>{}){}".format(substrate_pattern, substrate_end),
        r"\b(?:on|onto)\s+{}{}".format(substrate_alias_pattern, substrate_end),
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.I):
            substrate = match.groupdict().get("substrate")
            if substrate:
                _append_unique(values, _normalize_substrate_value(substrate))
                continue
            for index, (_pattern, normalized) in enumerate(COF_SUBSTRATE_ALIASES):
                alias_value = match.groupdict().get("alias_{}".format(index))
                if alias_value:
                    _append_unique(values, normalized)
                    break
    return values


def _split_monomer_phrase(
    phrase: str, *, trim_conditions: bool = True, split_or: bool = False
) -> list[str]:
    phrase = re.sub(r"\s+and\s+(?:a\s+)?stir\s+bar\b.*$", "", phrase, flags=re.I)
    if trim_conditions:
        phrase = re.sub(
            r"\b(?:in|at|under|using|with|by|through|via|to|for|affording|yielding)\b.*$",
            "",
            phrase,
            flags=re.I,
        )
    phrase = re.sub(
        r"\s+(?:and|,)\s+(?:investigated|characterized|studied|examined|analyzed|probed)\b.*$",
        "",
        phrase,
        flags=re.I,
    )
    phrase = re.sub(r"\s+", " ", phrase)
    separator = r"\s*(?:/|\+|\band\b|\bwith\b{})\s*".format(r"|\bor\b" if split_or else "")
    parts = re.split(separator, phrase, flags=re.I)
    names: list[str] = []
    for part in parts:
        name = clean_monomer_name(part)
        if not name or len(name) < 2:
            continue
        if name.lower() in MONOMER_STOP_WORDS_LOWER:
            continue
        if re.fullmatch(
            r"\d+(?:\.\d+)?\s*(?:{}|h|hours?|d|days?|months?)".format(TEMPERATURE_UNIT_PATTERN),
            name,
            flags=re.I,
        ):
            continue
        _append_unique(names, name)
    return names


def _append_monomer(monomers: list[dict], name: str, role: str) -> None:
    item = {"monomer": name, "role": role}
    if item not in monomers:
        monomers.append(item)


def heuristic_cof_monomers(text: str) -> list[dict]:
    monomers: list[dict] = []
    patterns = [
        (r"\bmonomers\s*(?:were|are|:)\s*([A-Za-z0-9][^.;]+?)(?=\s+(?:underwent|afforded)\b|[.;]|$)", "explicit"),
        (
            r"\bthree-component\s+polycondensation\s+of\s+([A-Za-z0-9][^.;]+?)"
            r"\s+with\s+a\s+molar\s+ratio\b",
            "polycondensation_list",
        ),
        (
            r"\b(?:tube|flask|vial)\s+was\s+filled\s+with\s+([A-Za-z0-9][A-Za-z0-9_-]*)\s*"
            r"\([^)]*\)\s*,\s*(?:PTSA|p-?TsOH|p-toluenesulfonic acid)\b",
            "reagent_list",
        ),
        (
            r"\bglass\s+tube\s+containing\s+[\d.]+\s+mg\s+of\s+([A-Za-z0-9][^.;]+?\([A-Za-z0-9-]+,\s*\d+%\))"
            r"\s*,\s*[\d.]+\s+mg\s+of\s+([A-Za-z0-9][^.;]+?\([A-Za-z0-9-]+,\s*\d+%\))"
            r"\s+and\s+[\d.]+\s+mL\s+of\s+mixed\s+solvent\b",
            "reagent_list",
        ),
        (
            r"\bof\s+([A-Za-z0-9][^.;]+?)\s+(?:and\s+(?:a\s+)?stir\s+bar\s+)?was\s+added\.\s+"
            r"Then\s+[\s\S]{0,120}?\bof\s+([A-Za-z0-9][^.;]+?)\s+was\s+added\b",
            "addition",
        ),
        (
            r"\busing\s+([A-Za-z0-9][^.;]+?)\s+and\s+([A-Za-z0-9][^.;]+?)"
            r"(?=,\s+(?:a\s+family\s+of\s+)?(?:[A-Za-z-]+linked\s+)?COFs?,)",
            "using",
        ),
        (
            r"\busing\s+([A-Za-z0-9][^.;]+?)\s+as\s+monomer\s+precursors?\b",
            "using",
        ),
        (
            r"\bco[\s-]?depositing\s+([A-Za-z0-9][^.;]+?)"
            r"(?=\s+(?:on|onto|under|at|in|to|through|via|for|using|with|by|affording|yielding)\b|[.;]|$)",
            "codeposition",
        ),
        (r"\bfrom\s+([A-Za-z0-9][^.;]+?)(?=\s+(?:by|under|using|at|in|to|through|via|for|affording|yielding)\b|[.;]|$)", "from"),
        (
            r"\breacting\s+([A-Za-z0-9][^.;]+?)\s+with\s+([A-Za-z0-9][^.;]+?)"
            r"(?=\s+(?:based\s+on|under|using|at|in|to|through|via|for|affording|yielding)\b|[.;]|$)",
            "reacting",
        ),
        (r"\bbetween\s+([A-Za-z0-9][^.;]+?)\s+and\s+([A-Za-z0-9][^.;]+?)(?=\s+(?:by|under|using|at|in|to|through|via|for|affording|yielding)\b|[.;]|$)", "between"),
        (r"\breaction\s+of\s+([A-Za-z0-9][^.;]+?)\s+with\s+([A-Za-z0-9][^.;]+?)(?=\s+(?:by|under|using|at|in|to|through|via|for|affording|yielding)\b|[.;]|$)", "reaction"),
        (r"\breaction\s+of\s+([A-Za-z0-9][^.;]+?)\s+and\s+([A-Za-z0-9][^.;]+?)(?=\s+(?:by|under|using|at|in|to|through|via|for|affording|yielding)\b|[.;]|$)", "reaction"),
        (r"\bcoupling\s+of\s+([A-Za-z0-9][^.;]+?)\s+with\s+([A-Za-z0-9][^.;]+?)(?=\s+(?:by|under|using|at|in|to|through|via|for|affording|yielding)\b|[.;]|$)", "coupling"),
        (r"\bcoupling\s+of\s+([A-Za-z0-9][^.;]+?)\s+and\s+([A-Za-z0-9][^.;]+?)(?=\s+(?:by|under|using|at|in|to|through|via|for|affording|yielding)\b|[.;]|$)", "coupling"),
        (r"\bcoupling\s+between\s+([A-Za-z0-9][^.;]+?)\s+and\s+([A-Za-z0-9][^.;]+?)(?=\s+(?:by|under|using|at|in|to|through|via|for|affording|yielding)\b|[.;]|$)", "coupling"),
        (r"\bcondensation\s+of\s+([A-Za-z0-9][^.;]+?)\s+with\s+([A-Za-z0-9][^.;]+?)(?=\s+(?:by|under|using|at|in|to|through|via|for|affording|yielding)\b|[.;]|$)", "condensation"),
        (r"\bcondensation\s+of\s+([A-Za-z0-9][^.;]+?)\s+and\s+([A-Za-z0-9][^.;]+?)(?=\s+(?:by|under|using|at|in|to|through|via|for|affording|yielding)\b|[.;]|$)", "condensation"),
        (r"\bcondensing\s+([A-Za-z0-9][^.;]+?)\s+with\s+([A-Za-z0-9][^.;]+?)(?=\s+(?:by|under|using|at|in|to|through|via|for|affording|yielding)\b|[.;]|$)", "condensation"),
        (r"\bpolymerization\s+of\s+([A-Za-z0-9][^.;]+?)\s+with\s+([A-Za-z0-9][^.;]+?)(?=\s+(?:by|under|using|at|in|to|through|via|for|affording|yielding)\b|[.;]|$)", "polymerization"),
        (r"\bpolymerization\s+of\s+([A-Za-z0-9][^.;]+?)\s+and\s+([A-Za-z0-9][^.;]+?)(?=\s+(?:by|under|using|at|in|to|through|via|for|affording|yielding)\b|[.;]|$)", "polymerization"),
        (r"\bpolycondensation\s+of\s+([A-Za-z0-9][^.;]+?)\s+with\s+(?!a\s+molar\s+ratio\b)([A-Za-z0-9][^.;]+?)(?=\s+(?:by|under|using|at|in|to|through|via|for|affording|yielding)\b|[.;]|$)", "polycondensation"),
        (r"\bpolycondensation\s+of\s+([A-Za-z0-9][^.;]+?)\s+and\s+([A-Za-z0-9][^.;]+?)(?=\s+(?:by|under|using|at|in|to|through|via|for|affording|yielding)\b|[.;]|$)", "polycondensation"),
    ]

    for pattern, role in patterns:
        for match in re.finditer(pattern, text, flags=re.I):
            if role == "polycondensation_list":
                for part in re.split(r"\s*,\s+|\s+and\s+", match.group(1), flags=re.I):
                    name = clean_monomer_name(part)
                    if name and name.lower() not in MONOMER_STOP_WORDS_LOWER:
                        _append_monomer(monomers, name, "polycondensation")
                continue
            if role == "polycondensation" and any(", " in group for group in match.groups()):
                continue
            if len(match.groups()) == 2:
                for group in match.groups():
                    for name in _split_monomer_phrase(
                        group, trim_conditions=role != "using", split_or=role == "reacting"
                    ):
                        _append_monomer(monomers, name, role)
            else:
                for name in _split_monomer_phrase(match.group(1)):
                    _append_monomer(monomers, name, role)
    return monomers


def heuristic_cof_fields(text: str) -> dict | None:
    if not is_cof_candidate_text(text):
        return None

    names = heuristic_cof_names(text)
    fields: dict = {}
    if names:
        fields["names"] = names

    routes = _route_values(text)
    if routes:
        fields["polymerization_routes"] = [{"route": route} for route in routes]

    linkages = _linkage_values(text)
    if linkages:
        fields["linkages"] = [{"linkage": linkage} for linkage in linkages]

    monomers = heuristic_cof_monomers(text)
    if monomers:
        fields["monomers"] = monomers

    catalysts = _catalyst_values(text)
    if catalysts:
        fields["catalysts"] = [{"catalyst": catalyst} for catalyst in catalysts]

    bases = _base_values(text)
    if bases:
        fields["bases"] = [{"base": base} for base in bases]

    solvents = _solvent_values(text)
    if solvents:
        fields["solvents"] = [{"solvent": solvent} for solvent in solvents]

    atmospheres = _atmosphere_values(text)
    if atmospheres:
        fields["atmospheres"] = [{"atmosphere": atmosphere} for atmosphere in atmospheres]

    interfaces = _interface_values(text)
    if interfaces:
        fields["interfaces"] = [{"interface": interface} for interface in interfaces]

    substrates = _substrate_values(text)
    if substrates:
        fields["substrates"] = [{"substrate": substrate} for substrate in substrates]

    temperatures = _temperature_values(text)
    if temperatures:
        fields["temperature"] = temperatures

    times = _time_values(text)
    if times:
        fields["time"] = times

    if not fields:
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
