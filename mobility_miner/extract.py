"""Conservative, evidence-preserving mobility extraction heuristics.

The first implementation deliberately does not depend on ChemDataExtractor.
This keeps it usable beside the vendored CDE 1.x fork and gives a future CDE2
adapter a stable normalized schema to target.
"""

from __future__ import annotations

import re
from typing import Any, Iterable


STANDARD_UNITS = "cm^2 V^-1 s^-1"

MOBILITY_SIGNAL_RE = re.compile(
    r"(?i)(?:\bmobilit(?:y|ies)\b|[\u03bc\u00b5]\s*[_-]?(?:e|h|electron|hole|ion)\b|\bmu\s*[_-](?:e|h)\b)"
)

SUPERSCRIPT_TRANSLATION = str.maketrans(
    {
        "\u2070": "0",
        "\u00b9": "1",
        "\u00b2": "2",
        "\u00b3": "3",
        "\u2074": "4",
        "\u2075": "5",
        "\u2076": "6",
        "\u2077": "7",
        "\u2078": "8",
        "\u2079": "9",
        "\u207b": "-",
        "\u2212": "-",
        "\u2013": "-",
        "\u2014": "-",
    }
)

BASE_NUMBER = r"(?:\d+(?:[.,]\d+)?|\.\d+)"
SCIENTIFIC_SUFFIX = (
    r"(?:\s*(?:[xX\u00d7\u00b7*]\s*10\s*(?:\^|\*\*)?\s*"
    r"(?:[-+\u2212\u2013\u2014]?\s*\d+|[\u207b\u2070\u00b9\u00b2\u00b3\u2074-\u2079]+)"
    r"|[eE]\s*[-+\u2212\u2013\u2014]?\s*\d+))?"
)
NUMBER = BASE_NUMBER + SCIENTIFIC_SUFFIX

AREA_UNIT = r"(?P<length_unit>cm|m)\s*(?:\^\s*\{?\s*2\s*\}?|2|\u00b2)"
INVERSE_ONE = r"(?:\^\s*\{?\s*[-\u2212\u2013\u2014]?\s*1\s*\}?|[-\u2212\u2013\u2014]\s*1|\u207b\u00b9)"
MOBILITY_UNIT = (
    AREA_UNIT
    + r"\s*(?:"
    + r"(?:[/\u00b7\u22c5]?\s*V\s*"
    + INVERSE_ONE
    + r"\s*(?:[/\u00b7\u22c5]?\s*s\s*"
    + INVERSE_ONE
    + r"))"
    + r"|(?:/\s*\(?\s*V\s*(?:[-\u2212\u2013\u2014\u00b7\u22c5*]\s*)?s\s*\)?)"
    + r"|(?:/\s*V\s*/\s*s)"
    + r")"
)

QUANTITY_RE = re.compile(
    r"(?P<comparator><=|>=|[<>~\u2248\u2264\u2265])?\s*"
    r"(?P<value1>"
    + NUMBER
    + r")"
    r"(?:\s*(?P<range_separator>\bto\b|\u2013|\u2014)\s*(?P<value2>"
    + NUMBER
    + r"))?"
    r"(?:\s*(?:\u00b1|\+/-)\s*(?P<uncertainty>"
    + NUMBER
    + r"))?\s*"
    r"(?P<raw_units>"
    + MOBILITY_UNIT
    + r")",
    flags=re.I,
)

PAIRED_QUANTITY_RE = re.compile(
    r"(?P<paired_value1>"
    + NUMBER
    + r")\s*(?:,\s*|\band\b\s+)(?P<paired_value2>"
    + NUMBER
    + r")\s*(?P<paired_raw_units>"
    + MOBILITY_UNIT.replace("?P<length_unit>", "?P<paired_length_unit>")
    + r")",
    flags=re.I,
)


EXPERIMENTAL_METHODS = [
    (r"\b(?:organic\s+)?field[-\s]?effect(?:\s+transistor(?:s)?|\s+mobilit(?:y|ies))\b|\bOFETs?\b|\bFETs?\b", "field-effect transistor"),
    (r"\bHall(?:[-\s]+effect)?(?:[-\s]+measurement(?:s)?)?\b", "Hall effect"),
    (r"\bspace[-\s]?charge[-\s]?limited\s+current\b|\bSCLC\b", "space-charge-limited current"),
    (r"\btime[-\s]?of[-\s]?flight\b|\bTOF\b", "time-of-flight"),
    (r"\btime[-\s]?resolved\s+microwave\s+conductivity\b|\bTRMC\b", "time-resolved microwave conductivity"),
    (
        r"\b(?:time[-\s]?resolved\s+terahertz\s+spectroscop\w*|optical[-\s]+pump\s+terahertz[-\s]+probe|"
        r"terahertz(?:\s+spectroscop\w*)?|THz(?:\s+spectroscop\w*)?|TRTS|OPTP)\b",
        "terahertz spectroscopy",
    ),
    (r"\bphoto[-\s]?CELIV\b|\bCELIV\b", "photo-CELIV"),
    (r"\btransient\s+photoconductivity\b", "transient photoconductivity"),
    (r"\bimpedance\s+spectroscop\w*\b", "impedance spectroscopy"),
]

COMPUTATIONAL_ALGORITHMS = [
    (
        r"\bdeformation[-\s)]*potential(?:\s+theory)?(?=\b|provided)|\bDPT\b",
        "deformation-potential theory",
    ),
    (r"\bBoltzmann\s+transport\s+equation\b|\bBTE\b", "Boltzmann transport equation"),
    (r"\bKubo[-\s\u2013\u2014]?Greenwood\b", "Kubo-Greenwood"),
    (r"\bMarcus(?:[-\s]+(?:theory|hopping|rate))?\b", "Marcus theory"),
    (r"\btransient[-\s]+locali[sz]ation\b", "transient localization"),
    (r"\bkinetic\s+Monte\s+Carlo\b|\bkMC\b", "kinetic Monte Carlo"),
    (r"\beffective[-\s]+mass\s+approximation\b", "effective-mass approximation"),
    (r"\b(?:Fr[o\u00f6]hlich|Frohlich)(?:[-\s]+polaron)?\b", "Frohlich-polaron model"),
    (r"\bOsaka(?:[-\s]+mobility)?\b", "Osaka mobility model"),
    (r"\b(?:density[-\s]+functional\s+theory|DFT)\b", "density-functional theory"),
    (r"\bfirst[-\s]+principles?\b|\bab\s+initio\b", "first-principles calculation"),
]

ANALYSIS_MODELS = [
    (r"\bDrude[-\s]?Smith\s+model\b", "Drude-Smith model"),
    (r"\bDrude\s+model\b", "Drude model"),
]

EFFECTIVE_MOBILITY_LABEL_RE = re.compile(
    r"(?i)\beffective\s+(?:charge[-\s]?carrier\s+(?:sum\s+)?)?mobilit(?:y|ies)\b"
)
MOBILITY_YIELD_PRODUCT_RE = re.compile(
    r"[\u03c6\u03d5](?:\s|[\u00b7\u22c5\u00d7*]|\(cid:\d+\))*[\u03bc\u00b5]"
)
LOWER_BOUND_RELATION_RE = re.compile(
    r"(?i)\b(?:represents?\s+)?(?:a\s+)?lower\s+bound(?:\s+for\s+[\u03bc\u00b5])?\b|"
    r"\bunderestimat(?:e|es|ed)\s+(?:of\s+)?(?:the\s+)?(?:true\s+)?(?:physical\s+)?(?:mobilit(?:y|ies)|values?)\b|"
    r"representsalowerboundfor[\u03bc\u00b5]"
)
FET_REGIME_RE = re.compile(r"(?i)\b(?P<regime>saturation|linear)\s+regime\b")

CARRIER_PATTERNS = [
    (r"\bambipolar\b", "ambipolar"),
    (r"\b(?:electrons?|electronic|n[-\s]?type)\b|[\u03bc\u00b5]\s*[_-]?e\b|\bmu\s*[_-]e\b", "electron"),
    (r"\b(?:holes?|p[-\s]?type)\b|[\u03bc\u00b5]\s*[_-]?h\b|\bmu\s*[_-]h\b", "hole"),
    (r"\bproton(?:ic)?\b", "proton"),
    (r"\b(?:ion|ionic|cation|anion)\b", "ion"),
]

DIRECTION_PATTERNS = [
    (r"\barmchair(?:\s+direction)?\b", "armchair"),
    (r"\bzigzag(?:\s+direction)?\b", "zigzag"),
    (r"\bin[-\s]?plane\b", "in-plane"),
    (r"\bout[-\s]?of[-\s]?plane\b", "out-of-plane"),
    (r"\balong\s+the\s+([abcxyz])[-\s]?axis\b", None),
    (r"\b([abcxyz])[-\s]?direction\b", None),
]

CURRENT_WORK_RE = re.compile(
    r"(?i)\b(?:in\s+this\s+(?:work|study)|herein|"
    r"we\s+(?:report|measure|measured|calculate|calculated|predict|predicted|obtain|obtained|extract|extracted|determine|determined|demonstrate|demonstrated|present)|"
    r"(?:the\s+)?measured\s+value|values?\s+(?:were\s+)?extracted\s+from|analysis\s+demonstrated)\b"
)
PRIOR_WORK_RE = re.compile(
    r"(?i)\b(?:previous(?:ly)?|earlier|prior\s+(?:work|study|report)|reported\s+by|report\s+of|"
    r"subsequent\s+measurements?|according\s+to|in\s+the\s+literature|literature\s+(?:value|report))\b"
)
CITATION_RE = re.compile(
    r"(?:\[(?:\d+[a-z]?(?:\s*[-,]\s*\d+[a-z]?)*?)\]|"
    r"\(\s*(?:ref\.?\s*)?\d+[a-z]?\s*\)|"
    r"\brefs?\.?(?:\s+|\s*\[)\d+|"
    r"(?<=[A-Za-z)])\d{1,3}(?:\s*,\s*\d{1,3})+)",
    re.I,
)
DOCUMENT_LOCATOR_RE = re.compile(
    r"(?i)\b(?:"
    r"(?P<figure>(?:Figure|Fig\.?)\s+S?\d+(?:[A-Za-z])?)|"
    r"(?P<table>Table\s+S?\d+(?:[A-Za-z])?)|"
    r"(?P<section>Section\s+[A-Za-z0-9.]+)|"
    r"(?P<supporting>(?:Supporting|Supplementary)\s+Information)"
    r")\b"
)
DEVICE_TYPE_RE = re.compile(
    r"(?i)\b(?:single[-\s]+crystal\s+field[-\s]*effect\s+transistor|"
    r"single[-\s]+crystal\s+FET|SC[-\s]?FET)\b"
)
SAMPLE_FORM_RE = re.compile(
    r"(?i)\b(?:single[-\s]+crystal|thin[-\s]+films?|films?)\b"
)
DRAIN_SOURCE_VOLTAGE_RE = re.compile(
    r"(?i)\bdrain[-\s]+source\s+(?:bias|voltage)\s*"
    r"(?:\(\s*V(?:\s*[Dd][Ss])?\s*\))?\s*(?:was|=|of)?\s*"
    r"(?P<value>[+\-\u2212\u2013\u2014]?\s*\d+(?:\.\d+)?)\s*V\b"
)
CONDITION_COVERAGE_FIELDS = (
    "material_identity",
    "synthesis_processing",
    "sample_form",
    "device_type",
    "device_fabrication",
    "fabrication_method",
    "device_geometry",
    "electrode",
    "drain_source_voltage",
    "substrate",
    "thickness",
)
BLOCKING_REVIEW_FLAGS = {
    "determination_unresolved",
    "citation_metadata_unresolved",
    "multiple_methods_near_value",
    "effective_mobility_definition_unresolved",
    "source_relation_mixed_or_ambiguous",
    "multiple_temperatures_unaligned",
    "multiple_directions_unaligned",
    "multiple_carriers_unaligned",
    "document_locator_unaligned",
    "material_unresolved",
    "multiple_materials_unaligned",
    "material_identity_ambiguous",
}

COMPUTATIONAL_CUE_RE = re.compile(
    r"(?i)\b(?:calculat(?:e|ed|ion)|comput(?:e|ed|ational)|predict(?:ed|ion)?|simulat(?:e|ed|ion)|theoretical(?:ly)?|estimated?\s+(?:from|using)|first[-\s]principles?|DFT)\b"
)
EXPERIMENTAL_CUE_RE = re.compile(
    r"(?i)\b(?:measur(?:e|ed|ement)|experiment(?:al|ally)?|device|transistor|Hall|SCLC|TOF|TRMC|THz|photoconductiv\w*)\b"
)


def _unique(values: Iterable[Any]) -> list[Any]:
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _plain_text(text: str) -> str:
    return " ".join(text.split())


def _parse_number(raw: str) -> float:
    normalized = raw.translate(SUPERSCRIPT_TRANSLATION)
    normalized = normalized.replace(" ", "").replace(",", ".")
    normalized = normalized.replace("\u00d7", "x").replace("\u00b7", "x").replace("*", "x")
    scientific = re.fullmatch(r"(?P<base>(?:\d+(?:\.\d+)?|\.\d+))[xX]10(?:\^|xx)?(?P<exponent>[-+]?\d+)", normalized)
    if scientific:
        return float(scientific.group("base")) * (10 ** int(scientific.group("exponent")))
    normalized = re.sub(r"[eE]\+", "e", normalized)
    return float(normalized)


def _standardize_value(value: float, length_unit: str) -> float:
    if length_unit.lower() == "m":
        value *= 10000.0
    return float("{:.12g}".format(value))


def _sentence_bounds(text: str, position: int) -> tuple[int, int]:
    boundaries = [
        match.end()
        for match in re.finditer(r"[.!?](?=\s+(?:[A-Z\[]|$)|$)", text)
    ]
    left_candidates = [boundary for boundary in boundaries if boundary <= position]
    right_candidates = [boundary for boundary in boundaries if boundary > position]
    start = max(left_candidates) if left_candidates else 0
    end = min(right_candidates) if right_candidates else len(text)
    return start, end


def _nearby_text(text: str, start: int, end: int, radius: int = 180) -> str:
    sentence_start, sentence_end = _sentence_bounds(text, start)
    return text[max(sentence_start, start - radius) : min(sentence_end, end + radius)]


def _extract_named_matches(text: str, aliases: list[tuple[str, str]]) -> list[dict[str, Any]]:
    matches = []
    for pattern, canonical in aliases:
        for match in re.finditer(pattern, text, flags=re.I):
            matches.append(
                {
                    "name": canonical,
                    "raw_text": match.group(0),
                    "span": {"start": match.start(), "end": match.end()},
                }
            )
    matches.sort(key=lambda item: (item["span"]["start"], item["span"]["end"]))
    deduplicated = []
    for item in matches:
        if any(existing["name"] == item["name"] for existing in deduplicated):
            continue
        deduplicated.append(item)
    return deduplicated


def _offset_named_matches(matches: list[dict[str, Any]], offset: int) -> list[dict[str, Any]]:
    """Translate named-match spans from a clause into evidence-text coordinates."""
    return [
        {
            **item,
            "span": {
                "start": offset + item["span"]["start"],
                "end": offset + item["span"]["end"],
            },
        }
        for item in matches
    ]


def _carrier_matches(text: str, offset: int = 0) -> list[dict[str, Any]]:
    matches = []
    for pattern, carrier in CARRIER_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.I):
            matches.append(
                {
                    "carrier": carrier,
                    "raw_text": match.group(0),
                    "span": {"start": offset + match.start(), "end": offset + match.end()},
                }
            )
    matches.sort(key=lambda item: (item["span"]["start"], item["span"]["end"]))
    return matches


def _span_distance(span: dict[str, int], start: int, end: int) -> int:
    if span["end"] < start:
        return start - span["end"]
    if span["start"] > end:
        return span["start"] - end
    return 0


def _carrier_attachment_rank(text: str, span: dict[str, int], start: int, end: int) -> int:
    """Prefer an adjacent explicit `for/of <carrier>` attachment when distances tie."""
    if span["start"] >= end:
        gap = text[end : span["start"]]
        if re.fullmatch(r"(?i)\s*(?:for|of)\s+", gap):
            return 0
    return 1


def _measurement_carrier(
    text: str,
    entry: dict[str, Any],
    quantity_entries: list[dict[str, Any]],
) -> tuple[str | None, dict[str, Any] | None, bool]:
    """Bind an explicit carrier without guessing an unresolved multi-carrier order."""
    clause, clause_start = _claim_clause(text, entry["start"], entry["end"])
    matches = _carrier_matches(clause, clause_start)
    if not matches:
        return None, None, False

    carriers = _unique(item["carrier"] for item in matches)
    if len(carriers) == 1:
        selected = min(
            matches,
            key=lambda item: _span_distance(item["span"], entry["start"], entry["end"]),
        )
        return selected["carrier"], selected, False

    quantity_span = entry.get("quantity_span")
    if quantity_span and re.search(r"(?i)\brespectively\b", clause):
        paired_entries = [item for item in quantity_entries if item.get("quantity_span") == quantity_span]
        if len(paired_entries) == len(carriers):
            entry_index = paired_entries.index(entry)
            selected_carrier = carriers[entry_index]
            selected = next(item for item in matches if item["carrier"] == selected_carrier)
            return selected_carrier, selected, False

    clause_end = clause_start + len(clause)
    clause_entries = [
        item
        for item in quantity_entries
        if clause_start <= item["start"] and item["end"] <= clause_end
    ]
    nearest_matches = []
    for candidate_entry in clause_entries:
        ranked = sorted(
            enumerate(matches),
            key=lambda pair: (
                _span_distance(pair[1]["span"], candidate_entry["start"], candidate_entry["end"]),
                _carrier_attachment_rank(
                    text,
                    pair[1]["span"],
                    candidate_entry["start"],
                    candidate_entry["end"],
                ),
                pair[1]["span"]["start"],
            ),
        )
        if not ranked or _span_distance(ranked[0][1]["span"], candidate_entry["start"], candidate_entry["end"]) > 160:
            return None, None, True
        if len(ranked) > 1:
            best_score = (
                _span_distance(ranked[0][1]["span"], candidate_entry["start"], candidate_entry["end"]),
                _carrier_attachment_rank(
                    text,
                    ranked[0][1]["span"],
                    candidate_entry["start"],
                    candidate_entry["end"],
                ),
            )
            second_score = (
                _span_distance(ranked[1][1]["span"], candidate_entry["start"], candidate_entry["end"]),
                _carrier_attachment_rank(
                    text,
                    ranked[1][1]["span"],
                    candidate_entry["start"],
                    candidate_entry["end"],
                ),
            )
            if best_score == second_score and ranked[0][1]["carrier"] != ranked[1][1]["carrier"]:
                return None, None, True
        nearest_matches.append(ranked[0])

    if len({match_index for match_index, _match in nearest_matches}) != len(nearest_matches):
        return None, None, True
    selected = nearest_matches[clause_entries.index(entry)][1]
    return selected["carrier"], selected, False


TEMPERATURE_RE = re.compile(
    r"(?i)\b(?:at\s+)?(-?\d+(?:\.\d+)?)\s*(K|\u00b0\s*C)\b|\b(?:room|ambient)[-\s]+temperature\b"
)


def _measurement_temperature(text: str, start: int, end: int) -> tuple[str | None, dict[str, Any] | None, bool]:
    """Bind one explicit temperature within the value's clause, or flag ambiguity."""
    clause, clause_start = _claim_clause(text, start, end)
    matches = list(TEMPERATURE_RE.finditer(clause))
    if len(matches) != 1:
        return None, None, len(matches) > 1
    match = matches[0]
    raw_text = match.group(0)
    evidence = {
        "raw_text": raw_text,
        "span": {"start": clause_start + match.start(), "end": clause_start + match.end()},
    }
    return _plain_text(re.sub(r"(?i)^at\s+", "", raw_text)), evidence, False


def _measurement_direction(text: str, start: int, end: int) -> tuple[str | None, dict[str, Any] | None, bool]:
    """Bind one explicit direction within the value's clause, or flag ambiguity."""
    clause, clause_start = _claim_clause(text, start, end)
    candidates = []
    for pattern, canonical in DIRECTION_PATTERNS:
        for match in re.finditer(pattern, clause, flags=re.I):
            direction = canonical or "{}-axis".format(match.group(1).lower())
            candidates.append((match.start(), match.end(), direction, match.group(0)))
    if not candidates:
        return None, None, False
    if len({candidate[2] for candidate in candidates}) > 1:
        return None, None, True
    candidate = min(candidates, key=lambda item: item[0])
    evidence = {
        "raw_text": candidate[3],
        "span": {"start": clause_start + candidate[0], "end": clause_start + candidate[1]},
    }
    return candidate[2], evidence, False


def _citation_markers(text: str) -> list[str]:
    return _unique(_plain_text(match.group(0)) for match in CITATION_RE.finditer(text))


def _source_relation_details(text: str, offset: int = 0) -> tuple[str, list[dict[str, Any]]]:
    """Return claim provenance and the exact cues supporting that decision."""
    current_matches = list(CURRENT_WORK_RE.finditer(text))
    prior_matches = list(PRIOR_WORK_RE.finditer(text))
    if current_matches and prior_matches:
        relation = "mixed_or_ambiguous"
        selected = [("current_work", match) for match in current_matches]
        selected += [("prior_work", match) for match in prior_matches]
    elif current_matches:
        relation = "current_work"
        selected = [("current_work", match) for match in current_matches]
    elif prior_matches:
        relation = "prior_work"
        selected = [("prior_work", match) for match in prior_matches]
    else:
        return "unspecified", []

    evidence = [
        {
            "cue_type": cue_type,
            "raw_text": match.group(0),
            "span": {"start": offset + match.start(), "end": offset + match.end()},
        }
        for cue_type, match in selected
    ]
    return relation, evidence


def _source_relation(text: str) -> str:
    return _source_relation_details(text)[0]


def _document_locator_matches(text: str, offset: int = 0) -> list[dict[str, Any]]:
    """Return explicit figure/table/section/SI locators with exact spans."""
    locators = []
    for match in DOCUMENT_LOCATOR_RE.finditer(text):
        locator_type = next(name for name, value in match.groupdict().items() if value)
        locators.append(
            {
                "locator_type": locator_type,
                "raw_text": match.group(0),
                "span": {"start": offset + match.start(), "end": offset + match.end()},
            }
        )
    return locators


def _condition_scope(text: str, start: int, end: int) -> tuple[str, int]:
    """Narrow conditions to the value's clause and figure-panel segment."""
    clause, clause_start = _claim_clause(text, start, end)
    local_start = start - clause_start
    local_end = end - clause_start
    boundaries = [(match.start(), match.end()) for match in re.finditer(r"\([a-h]\)", clause, flags=re.I)]
    segment_start = max(
        (boundary_end for _boundary_start, boundary_end in boundaries if boundary_end <= local_start),
        default=0,
    )
    segment_end = min(
        (boundary_start for boundary_start, _boundary_end in boundaries if boundary_start >= local_end),
        default=len(clause),
    )
    return clause[segment_start:segment_end], clause_start + segment_start


def _condition_matches(text: str, offset: int = 0) -> list[dict[str, Any]]:
    """Extract explicit sample/device/operating-condition candidates."""
    conditions = []
    for match in DEVICE_TYPE_RE.finditer(text):
        conditions.append(
            {
                "field": "device_type",
                "value": "single-crystal field-effect transistor",
                "raw_text": match.group(0),
                "span": {"start": offset + match.start(), "end": offset + match.end()},
            }
        )
    for match in SAMPLE_FORM_RE.finditer(text):
        raw_text = match.group(0)
        if re.search(r"(?i)single", raw_text):
            value = "single crystal"
        elif re.search(r"(?i)thin", raw_text):
            value = "thin film"
        else:
            value = "film"
        conditions.append(
            {
                "field": "sample_form",
                "value": value,
                "raw_text": raw_text,
                "span": {"start": offset + match.start(), "end": offset + match.end()},
            }
        )
    for match in DRAIN_SOURCE_VOLTAGE_RE.finditer(text):
        raw_value = match.group("value")
        normalized_value = float(
            raw_value.replace(" ", "")
            .replace("\u2212", "-")
            .replace("\u2013", "-")
            .replace("\u2014", "-")
        )
        conditions.append(
            {
                "field": "drain_source_voltage",
                "value": "{} V".format(_plain_text(raw_value)),
                "normalized_value": normalized_value,
                "normalized_unit": "V",
                "raw_text": match.group(0),
                "span": {"start": offset + match.start(), "end": offset + match.end()},
            }
        )
    conditions.sort(key=lambda item: (item["span"]["start"], item["span"]["end"], item["field"]))
    return conditions


def _measurement_conditions(
    text: str,
    start: int,
    end: int,
    block_conditions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Bind unique panel/clause-local conditions and expose missingness."""
    scope, scope_start = _condition_scope(text, start, end)
    local_conditions = _condition_matches(scope, scope_start)
    records = []
    coverage = []
    review_flags = []
    for field in CONDITION_COVERAGE_FIELDS:
        local = [item for item in local_conditions if item["field"] == field]
        block = [item for item in block_conditions if item["field"] == field]
        distinct_values = _unique(item["value"] for item in local)
        if len(distinct_values) == 1:
            selected = min(
                local,
                key=lambda item: _span_distance(item["span"], start, end),
            )
            record = {
                **selected,
                "binding_scope": "measurement",
                "review_flags": [],
            }
            records.append(record)
            coverage.append(
                {"field": field, "status": "reported", "condition_refs": [len(records) - 1]}
            )
        elif len(distinct_values) > 1:
            coverage.append({"field": field, "status": "ambiguous"})
            review_flags.append("{}_ambiguous".format(field))
        elif block:
            coverage.append({"field": field, "status": "not_aligned"})
            review_flags.append("{}_not_aligned".format(field))
        else:
            coverage.append({"field": field, "status": "not_reported"})
    return records, coverage, review_flags


def _claim_clause(text: str, start: int, end: int) -> tuple[str, int]:
    """Narrow provenance to the contrast/semicolon clause containing a value."""
    sentence_start, sentence_end = _sentence_bounds(text, start)
    sentence = text[sentence_start:sentence_end]
    local_start = start - sentence_start
    local_end = end - sentence_start
    boundaries = [
        (match.start(), match.end())
        for match in re.finditer(
            r"(?i);|\b(?:whereas|while|but)\b|"
            r"\b(?:is|are|was|were)\s+(?:in\s+(?:excellent\s+)?agreement\s+with|consistent\s+with)|"
            r"\b(?:agrees?\s+with|compared\s+(?:with|to))\b",
            sentence,
        )
    ]
    clause_start = max(
        (boundary_end for _boundary_start, boundary_end in boundaries if boundary_end <= local_start),
        default=0,
    )
    clause_end = min(
        (boundary_start for boundary_start, _boundary_end in boundaries if boundary_start >= local_end),
        default=len(sentence),
    )
    absolute_start = sentence_start + clause_start
    return sentence[clause_start:clause_end], absolute_start


def _nearest_match(matches: Iterable[re.Match[str]], start: int, end: int) -> re.Match[str] | None:
    candidates = []
    for match in matches:
        if match.end() < start:
            distance = start - match.end()
        elif match.start() > end:
            distance = match.start() - end
        else:
            distance = 0
        candidates.append((distance, match.start(), match))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][2]


def _quantity_semantics(text: str, start: int, end: int) -> dict[str, Any]:
    """Preserve explicit effective-mobility semantics for one quantity.

    A reported ``phi * mu`` product has mobility units but is not a direct
    mobility measurement.  The distinction is attached at quantity level so a
    later record linker cannot silently merge it with a true ``mu`` value.
    """
    sentence_start, sentence_end = _sentence_bounds(text, start)
    sentence = text[sentence_start:sentence_end]
    local_start = start - sentence_start
    local_end = end - sentence_start

    contrast_boundaries = [
        (match.start(), match.end())
        for match in re.finditer(r"(?i)\b(?:whereas|while|but)\b", sentence)
    ]
    clause_start = max(
        (boundary_end for _boundary_start, boundary_end in contrast_boundaries if boundary_end <= local_start),
        default=0,
    )
    clause_end = min(
        (boundary_start for boundary_start, _boundary_end in contrast_boundaries if boundary_start >= local_end),
        default=len(sentence),
    )
    clause = sentence[clause_start:clause_end]
    clause_local_start = local_start - clause_start
    clause_local_end = local_end - clause_start

    label_match = _nearest_match(EFFECTIVE_MOBILITY_LABEL_RE.finditer(clause), clause_local_start, clause_local_end)
    product_match = _nearest_match(MOBILITY_YIELD_PRODUCT_RE.finditer(clause), clause_local_start, clause_local_end)
    if not label_match and not product_match:
        return {}

    qualifier_match = label_match or product_match
    assert qualifier_match is not None
    semantics: dict[str, Any] = {
        "quantity_kind": "mobility_yield_product" if product_match else "effective_mobility",
        "quantity_label": {
            "raw_text": qualifier_match.group(0),
            "span": {
                "start": sentence_start + clause_start + qualifier_match.start(),
                "end": sentence_start + clause_start + qualifier_match.end(),
            },
        },
    }
    relation_match = _nearest_match(
        LOWER_BOUND_RELATION_RE.finditer(clause),
        clause_local_start,
        clause_local_end,
    )
    if relation_match:
        semantics["mobility_relation"] = {
            "relation": "lower_bound_of_true_mobility",
            "raw_text": relation_match.group(0),
            "span": {
                "start": sentence_start + clause_start + relation_match.start(),
                "end": sentence_start + clause_start + relation_match.end(),
            },
        }
    return semantics


def _measurement_regime(text: str, start: int, end: int) -> dict[str, Any] | None:
    """Bind an explicit FET operating regime to its nearest value in a sentence."""
    sentence_start, sentence_end = _sentence_bounds(text, start)
    sentence = text[sentence_start:sentence_end]
    local_start = start - sentence_start
    local_end = end - sentence_start
    contrast_boundaries = [
        (candidate.start(), candidate.end())
        for candidate in re.finditer(r"(?i)\b(?:whereas|while|but)\b", sentence)
    ]
    clause_start = max(
        (boundary_end for _boundary_start, boundary_end in contrast_boundaries if boundary_end <= local_start),
        default=0,
    )
    clause_end = min(
        (boundary_start for boundary_start, _boundary_end in contrast_boundaries if boundary_start >= local_end),
        default=len(sentence),
    )
    clause = sentence[clause_start:clause_end]
    match = _nearest_match(
        FET_REGIME_RE.finditer(clause),
        local_start - clause_start,
        local_end - clause_start,
    )
    if not match:
        return None
    return {
        "regime": match.group("regime").lower(),
        "raw_text": match.group(0),
        "span": {
            "start": sentence_start + clause_start + match.start(),
            "end": sentence_start + clause_start + match.end(),
        },
    }


def _determination(text: str, methods: list[dict[str, Any]], algorithms: list[dict[str, Any]]) -> str:
    has_computational = bool(algorithms or COMPUTATIONAL_CUE_RE.search(text))
    has_experimental = bool(methods or EXPERIMENTAL_CUE_RE.search(text))
    if has_computational and has_experimental:
        return "mixed_or_ambiguous"
    if has_computational:
        return "computational"
    if has_experimental:
        return "experimental"
    if PRIOR_WORK_RE.search(text) or re.search(r"(?i)\breported\b", text):
        return "reported_unspecified"
    return "unspecified"


def _clean_material(raw: str) -> str | None:
    material = _plain_text(raw).strip(" ,;:()")
    material = re.sub(r"(?i)^(?:the|a|an)\s+", "", material)
    material = re.sub(r"(?i)\s+(?:sample|film|crystal|material)$", "", material)
    if not material or len(material) > 90:
        return None
    if re.match(r"^[+\-~\u2248\u2264\u2265<>=]?\s*(?:\d|\.)", material):
        return None
    if not re.search(r"[A-Za-z]", material):
        return None
    rejected = {
        "electron",
        "electrons",
        "hole",
        "holes",
        "carrier",
        "carriers",
        "charge carriers",
        "this material",
        "the material",
        "has",
        "have",
        "it",
        "that",
        "crystal",
        "crystals",
    }
    if material.lower() in rejected:
        return None
    if re.search(r"(?i)\b(?:was|were|is|are|reached|reported|measured|calculated)\b", material):
        return None
    if re.search(r"(?i)\b(?:axis|plane|direction|content|devices?|applications?|values?|films?|logic)\b", material):
        return None
    if re.search(r"(?i)\b(?:Supporting|Supplementary)\s+Information\b", material):
        return None
    if " " in material and material.lower() == material and not re.search(r"\d", material):
        return None
    return material


def extract_materials(text: str) -> list[dict[str, Any]]:
    """Extract conservative material-name candidates near mobility wording."""
    patterns = [
        r"(?i)^\s*(?P<material>[A-Za-z0-9][A-Za-z0-9\-+()\[\]/.\u00b7\u2013\u2014]{1,60})\s*\|[^|]{0,100}\bmobilit(?:y|ies)\b",
        r"(?i)\bmobilit(?:y|ies)\s+(?:of|in|for)\s+(?:electrons?\s+|holes?\s+|charge\s+carriers?\s+)?(?P<material>[A-Za-z0-9][A-Za-z0-9\-+()\[\]/.\u00b7\u2013\u2014\s]{1,80}?)(?=\s+(?:was|were|is|are|reached|reaches|amounted|has|have|can|along|at)\b|[,;:]|\.(?:\s|$))",
        r"(?i)\b(?:electron|hole|carrier|charge[-\s]?carrier|ionic|proton)\s+mobilit(?:y|ies)\s+(?:of|in|for)\s+(?P<material>[A-Za-z0-9][A-Za-z0-9\-+()\[\]/.\u00b7\u2013\u2014\s]{1,80}?)(?=\s+(?:was|were|is|are|reached|reaches|amounted|has|have|can|along|at)\b|[,;:]|\.(?:\s|$))",
        r"(?i)\bfor\s+(?P<material>[A-Za-z0-9][A-Za-z0-9\-+()\[\]/.\u00b7\u2013\u2014\s]{1,60}?),\s+(?:the\s+)?(?:electron|hole|carrier|charge[-\s]?carrier|ionic|proton)?\s*mobilit(?:y|ies)\b",
        r"(?P<material>[A-Z][A-Za-z0-9\-+()\[\]/.\u00b7\u2013\u2014]{1,50})\s+(?i:(?:exhibit(?:s|ed)?|show(?:s|ed)?|possess(?:es|ed)?|display(?:s|ed)?)\s+(?:an?\s+)?(?:electron|hole|carrier|charge[-\s]?carrier|field[-\s]?effect)?\s*mobilit(?:y|ies))\b",
        r"(?i:mobility\s*is\s*associated\s*with)\s*"
        r"(?P<material>[A-Z][A-Za-z0-9\-+()\[\]/.\u00b7\u2013\u2014]{1,60}?)"
        r"(?=(?i:\s*with\s*an?\s*approximate\s*value))",
    ]
    materials = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            material = _clean_material(match.group("material"))
            if material and material not in [item["material"] for item in materials]:
                materials.append(
                    {
                        "material": material,
                        "raw_text": match.group("material"),
                        "span": {
                            "start": match.start("material"),
                            "end": match.end("material"),
                        },
                    }
                )

    for entry in _quantity_entries(text):
        clause, clause_start = _claim_clause(text, entry["start"], entry["end"])
        if not MOBILITY_SIGNAL_RE.search(clause):
            continue
        tail_start = entry["end"] - clause_start
        if tail_start < 0 or tail_start > len(clause):
            continue
        match = re.match(
            r"^\s+(?i:for)\s+"
            r"(?P<material>[A-Z][A-Za-z0-9\-+()\[\]/.\u00b7\u2013\u2014]{1,50})"
            r"(?=[,;.]|\s+(?i:which|that)\b)",
            clause[tail_start:],
        )
        if not match:
            continue
        material = _clean_material(match.group("material"))
        if not material or material in [item["material"] for item in materials]:
            continue
        material_start = clause_start + tail_start + match.start("material")
        materials.append(
            {
                "material": material,
                "raw_text": match.group("material"),
                "span": {
                    "start": material_start,
                    "end": clause_start + tail_start + match.end("material"),
                },
                "binding_basis": "post_value_for_phrase",
            }
        )
    materials.sort(key=lambda item: (item["span"]["start"], item["span"]["end"]))
    return materials


def is_mobility_candidate_text(text: str) -> bool:
    """Return whether a text block contains an explicit mobility signal."""
    return bool(MOBILITY_SIGNAL_RE.search(text))


def _quantity_entries(text: str) -> list[dict[str, Any]]:
    """Return scalar/range quantities, expanding shared-unit value pairs."""
    entries = []
    paired_spans = []
    for match in PAIRED_QUANTITY_RE.finditer(text):
        paired_spans.append((match.start(), match.end()))
        for group_name in ("paired_value1", "paired_value2"):
            entries.append(
                {
                    "start": match.start(group_name),
                    "end": match.end(group_name),
                    "raw_value": match.group(group_name),
                    "value1": _parse_number(match.group(group_name)),
                    "value2": None,
                    "uncertainty": None,
                    "comparator": None,
                    "raw_units": match.group("paired_raw_units"),
                    "length_unit": match.group("paired_length_unit"),
                    "span_text": match.group(group_name),
                    "quantity_span": {
                        "start": match.start(),
                        "end": match.end(),
                        "text": match.group(0),
                    },
                }
            )

    for match in QUANTITY_RE.finditer(text):
        if any(start <= match.start() and match.end() <= end for start, end in paired_spans):
            continue
        entries.append(
            {
                "start": match.start(),
                "end": match.end(),
                "raw_value": _plain_text(
                    text[
                        match.start("comparator") if match.group("comparator") else match.start("value1") :
                        match.end("uncertainty") if match.group("uncertainty") else
                        match.end("value2") if match.group("value2") else
                        match.end("value1")
                    ]
                ),
                "value1": _parse_number(match.group("value1")),
                "value2": _parse_number(match.group("value2")) if match.group("value2") else None,
                "uncertainty": _parse_number(match.group("uncertainty")) if match.group("uncertainty") else None,
                "comparator": match.group("comparator"),
                "raw_units": match.group("raw_units"),
                "length_unit": match.group("length_unit"),
                "span_text": match.group(0),
                "quantity_span": None,
            }
        )
    entries.sort(key=lambda item: (item["start"], item["end"]))
    return entries


def extract_mobility_measurements(
    text: str,
    methods: list[dict[str, Any]] | None = None,
    algorithms: list[dict[str, Any]] | None = None,
    analysis_models: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Extract mobility quantities and attach nearby claim context."""
    methods = methods or []
    algorithms = algorithms or []
    analysis_models = analysis_models or []
    measurements = []
    quantity_entries = _quantity_entries(text)
    block_conditions = _condition_matches(text)

    for entry in quantity_entries:
        sentence_start, sentence_end = _sentence_bounds(text, entry["start"])
        sentence = text[sentence_start:sentence_end]
        if not MOBILITY_SIGNAL_RE.search(sentence):
            nearby = _nearby_text(text, entry["start"], entry["end"])
            if not MOBILITY_SIGNAL_RE.search(nearby):
                continue
        else:
            nearby = sentence

        standard_value1 = _standardize_value(entry["value1"], entry["length_unit"])
        standard_value2 = _standardize_value(entry["value2"], entry["length_unit"]) if entry["value2"] is not None else None
        standard_uncertainty = _standardize_value(entry["uncertainty"], entry["length_unit"]) if entry["uncertainty"] is not None else None

        claim_clause, claim_clause_start = _claim_clause(text, entry["start"], entry["end"])
        local_methods = _offset_named_matches(
            _extract_named_matches(claim_clause, EXPERIMENTAL_METHODS),
            claim_clause_start,
        )
        local_algorithms = _offset_named_matches(
            _extract_named_matches(claim_clause, COMPUTATIONAL_ALGORITHMS),
            claim_clause_start,
        )
        local_analysis_models = _offset_named_matches(
            _extract_named_matches(claim_clause, ANALYSIS_MODELS),
            claim_clause_start,
        )
        method_from_paragraph = False
        algorithm_from_paragraph = False
        analysis_model_from_paragraph = False
        if not local_methods and len(methods) == 1:
            local_methods = methods
            method_from_paragraph = True
        if not local_algorithms and len(algorithms) == 1:
            local_algorithms = algorithms
            algorithm_from_paragraph = True
        if not local_analysis_models and len(analysis_models) == 1:
            local_analysis_models = analysis_models
            analysis_model_from_paragraph = True
        carrier, carrier_evidence, carrier_ambiguous = _measurement_carrier(
            text,
            entry,
            quantity_entries,
        )

        source_relation, source_relation_evidence = _source_relation_details(
            claim_clause,
            offset=claim_clause_start,
        )
        document_locators = _document_locator_matches(claim_clause, claim_clause_start)
        condition_records, condition_coverage, condition_review_flags = _measurement_conditions(
            text,
            entry["start"],
            entry["end"],
            block_conditions,
        )
        measurement: dict[str, Any] = {
            "raw_value": _plain_text(entry["raw_value"]),
            "raw_units": _plain_text(entry["raw_units"]),
            "standard_units": STANDARD_UNITS,
            "value": standard_value1,
            "span": {"start": entry["start"], "end": entry["end"], "text": entry["span_text"]},
            "determination": _determination(claim_clause, local_methods, local_algorithms),
            "source_relation": source_relation,
            "condition_coverage": condition_coverage,
        }
        if source_relation_evidence:
            measurement["source_relation_evidence"] = source_relation_evidence
        if document_locators:
            measurement["document_locators"] = document_locators
        if condition_records:
            measurement["condition_records"] = condition_records
        measurement.update(_quantity_semantics(text, entry["start"], entry["end"]))
        regime = _measurement_regime(text, entry["start"], entry["end"])
        if regime:
            measurement["measurement_regime"] = regime
        if entry["quantity_span"]:
            measurement["quantity_span"] = entry["quantity_span"]
        if entry["comparator"]:
            measurement["comparator"] = entry["comparator"].replace("\u2264", "<=").replace("\u2265", ">=").replace("\u2248", "~")
        if standard_value2 is not None:
            measurement["value_range"] = [standard_value1, standard_value2]
            measurement.pop("value", None)
        if standard_uncertainty is not None:
            measurement["uncertainty"] = standard_uncertainty
        if carrier:
            measurement["carrier"] = carrier
            measurement["carrier_evidence"] = carrier_evidence
        temperature, temperature_evidence, temperature_ambiguous = _measurement_temperature(
            text, entry["start"], entry["end"]
        )
        if temperature:
            measurement["temperature"] = temperature
            measurement["temperature_evidence"] = temperature_evidence
        direction, direction_evidence, direction_ambiguous = _measurement_direction(
            text, entry["start"], entry["end"]
        )
        if direction:
            measurement["direction"] = direction
            measurement["direction_evidence"] = direction_evidence
        if local_methods:
            measurement["methods"] = [item["name"] for item in local_methods]
            measurement["method_evidence"] = [
                {"method": item["name"], "raw_text": item["raw_text"], "span": item["span"]}
                for item in local_methods
            ]
        if local_algorithms:
            measurement["algorithms"] = [item["name"] for item in local_algorithms]
            measurement["algorithm_evidence"] = [
                {"algorithm": item["name"], "raw_text": item["raw_text"], "span": item["span"]}
                for item in local_algorithms
            ]
        if local_analysis_models:
            measurement["analysis_models"] = [item["name"] for item in local_analysis_models]
            measurement["analysis_model_evidence"] = [
                {"analysis_model": item["name"], "raw_text": item["raw_text"], "span": item["span"]}
                for item in local_analysis_models
            ]
        citations = _citation_markers(nearby)
        if citations:
            measurement["citation_markers"] = citations

        review_flags = []
        if measurement["determination"] in {"unspecified", "reported_unspecified", "mixed_or_ambiguous"}:
            review_flags.append("determination_unresolved")
        if measurement["source_relation"] == "prior_work" and not citations:
            review_flags.append("citation_metadata_unresolved")
        if len(measurement.get("methods", [])) + len(measurement.get("algorithms", [])) > 1:
            review_flags.append("multiple_methods_near_value")
        if method_from_paragraph:
            review_flags.append("method_from_paragraph_context")
        if algorithm_from_paragraph:
            review_flags.append("algorithm_from_paragraph_context")
        if analysis_model_from_paragraph:
            review_flags.append("analysis_model_from_paragraph_context")
        if measurement.get("quantity_kind") == "mobility_yield_product":
            review_flags.append("reported_quantity_is_not_direct_mobility")
        elif measurement.get("quantity_kind") == "effective_mobility":
            review_flags.append("effective_mobility_definition_unresolved")
        if measurement["source_relation"] == "mixed_or_ambiguous":
            review_flags.append("source_relation_mixed_or_ambiguous")
        if temperature_ambiguous:
            review_flags.append("multiple_temperatures_unaligned")
        if direction_ambiguous:
            review_flags.append("multiple_directions_unaligned")
        if carrier_ambiguous:
            review_flags.append("multiple_carriers_unaligned")
        review_flags.extend(condition_review_flags)
        if review_flags:
            measurement["review_flags"] = review_flags
        measurements.append(measurement)

    return measurements


def refresh_measurement_review_status(measurement: dict[str, Any]) -> str:
    """Summarize review flags as an actionable measurement-level state."""
    flags = _unique(measurement.get("review_flags", []))
    if flags:
        measurement["review_flags"] = flags
    else:
        measurement.pop("review_flags", None)

    reasons = list(flags)
    if measurement.get("source_relation") == "unspecified":
        reasons.append("source_relation_unspecified")
    reasons = _unique(reasons)
    blocking = any(
        flag in BLOCKING_REVIEW_FLAGS
        or flag.endswith("_not_aligned")
        or flag.endswith("_ambiguous")
        for flag in flags
    )
    if blocking:
        status = "BLOCKED"
    elif reasons:
        status = "REVIEW"
    else:
        status = "READY"
    measurement["review_status"] = status
    if reasons:
        measurement["review_status_reasons"] = reasons
    else:
        measurement.pop("review_status_reasons", None)
    return status


def extract_mobility_fields(text: str) -> dict[str, Any] | None:
    """Extract normalized mobility data, methods, algorithms, and provenance."""
    if not is_mobility_candidate_text(text):
        return None

    methods = _extract_named_matches(text, EXPERIMENTAL_METHODS)
    algorithms = _extract_named_matches(text, COMPUTATIONAL_ALGORITHMS)
    analysis_models = _extract_named_matches(text, ANALYSIS_MODELS)
    block_conditions = _condition_matches(text)
    measurements = extract_mobility_measurements(
        text,
        methods=methods,
        algorithms=algorithms,
        analysis_models=analysis_models,
    )
    document_locators = _document_locator_matches(text)

    if not measurements and not methods and not algorithms:
        return None

    fields: dict[str, Any] = {}
    materials = extract_materials(text)
    if materials:
        fields["materials"] = materials
    if measurements:
        if document_locators:
            for measurement in measurements:
                if not measurement.get("document_locators"):
                    measurement.setdefault("review_flags", []).append("document_locator_unaligned")
        if not materials:
            for measurement in measurements:
                measurement.setdefault("review_flags", []).append("material_unresolved")
        elif len(materials) == 1:
            for measurement in measurements:
                measurement["material_refs"] = [0]
                conditions = measurement.setdefault("condition_records", [])
                conditions.append(
                    {
                        "field": "material_identity",
                        "value": materials[0]["material"],
                        "raw_text": materials[0]["raw_text"],
                        "span": dict(materials[0]["span"]),
                        "binding_scope": "material",
                        "material_refs": [0],
                        "review_flags": [],
                    }
                )
                for coverage in measurement["condition_coverage"]:
                    if coverage["field"] == "material_identity":
                        coverage.update(
                            {"status": "reported", "condition_refs": [len(conditions) - 1]}
                        )
        elif len(materials) > 1:
            for measurement in measurements:
                measurement.setdefault("review_flags", []).append("multiple_materials_unaligned")
                measurement.setdefault("review_flags", []).append("material_identity_ambiguous")
                for coverage in measurement["condition_coverage"]:
                    if coverage["field"] == "material_identity":
                        coverage["status"] = "ambiguous"
        fields["mobilities"] = measurements
        bound_condition_spans = {
            (condition["span"]["start"], condition["span"]["end"], condition["field"])
            for measurement in measurements
            for condition in measurement.get("condition_records", [])
        }
        unbound_conditions = [
            {
                **condition,
                "binding_scope": "document",
                "review_flags": ["not_bound_to_measurement"],
            }
            for condition in block_conditions
            if (
                condition["span"]["start"],
                condition["span"]["end"],
                condition["field"],
            )
            not in bound_condition_spans
        ]
        if unbound_conditions:
            fields["condition_candidates"] = unbound_conditions
    if document_locators:
        fields["document_locators"] = document_locators
    if methods:
        fields["measurement_methods"] = [
            {"method": item["name"], "raw_text": item["raw_text"], "span": item["span"]}
            for item in methods
        ]
    if algorithms:
        fields["computational_algorithms"] = [
            {"algorithm": item["name"], "raw_text": item["raw_text"], "span": item["span"]}
            for item in algorithms
        ]
    if analysis_models:
        fields["analysis_models"] = [
            {"model": item["name"], "raw_text": item["raw_text"], "span": item["span"]}
            for item in analysis_models
        ]
    for measurement in measurements:
        refresh_measurement_review_status(measurement)
    return fields


def _source_evidence_ref(source: dict[str, Any], span: dict[str, Any]) -> dict[str, Any]:
    evidence_ref = {
        "source_id": source.get("id"),
        "source_kind": source.get("kind"),
        "span": dict(span),
    }
    for key in (
        "page", "paragraph_index", "block_index", "element_type",
        "doi", "doi_source", "document_title",
    ):
        if source.get(key) is not None:
            evidence_ref[key] = source[key]
    return evidence_ref


def _normalized_condition(condition: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(condition)
    normalized["evidence_refs"] = [_source_evidence_ref(source, condition["span"])]
    return normalized


def normalized_mobility_item(source: dict[str, Any], evidence_text: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Build a stable, evidence-first record for a candidate text block."""
    record_fields = dict(fields)
    if fields.get("condition_candidates"):
        record_fields["condition_candidates"] = [
            _normalized_condition(condition, source)
            for condition in fields["condition_candidates"]
        ]
    if fields.get("mobilities"):
        mobilities = []
        for measurement in fields["mobilities"]:
            normalized_measurement = dict(measurement)
            normalized_measurement["evidence_refs"] = [
                _source_evidence_ref(source, measurement["span"])
            ]
            if measurement.get("condition_records"):
                normalized_measurement["condition_records"] = [
                    _normalized_condition(condition, source)
                    for condition in measurement["condition_records"]
                ]
            mobilities.append(normalized_measurement)
        record_fields["mobilities"] = mobilities
    return {
        "schema_version": "mobility_miner/0.1",
        "record_type": "charge_carrier_mobility",
        "source": source,
        "fields": record_fields,
        "evidence_text": evidence_text,
        "passes_mobility_filter": bool(fields.get("mobilities")),
        "extraction_method": "mobility_evidence_heuristic",
    }
