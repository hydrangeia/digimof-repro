"""Reviewable HTML report for mobility evidence records."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Iterable


def _plain(value: Any) -> str:
    return " ".join(str(value).split())


def _materials(record: dict[str, Any]) -> list[str]:
    return [
        item.get("material", "")
        for item in record.get("fields", {}).get("materials", [])
        if isinstance(item, dict) and item.get("material")
    ]


def _format_number(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    return "{:.6g}".format(value)


def _measurement_value(measurement: dict[str, Any]) -> str:
    if measurement.get("value_range"):
        value = "{}-{}".format(*[_format_number(item) for item in measurement["value_range"]])
    else:
        value = _format_number(measurement.get("value"))
    if measurement.get("uncertainty") is not None:
        value += " +/- {}".format(_format_number(measurement["uncertainty"]))
    return "{}{} {}".format(measurement.get("comparator", ""), value, measurement.get("standard_units", "")).strip()


def _badge_list(values: list[str]) -> str:
    if not values:
        return '<span class="muted">-</span>'
    return "".join('<span class="badge">{}</span>'.format(escape(_plain(value))) for value in values)


def _highlight_evidence(record: dict[str, Any]) -> str:
    text = record.get("evidence_text", "")
    spans = []
    for container in record.get("fields", {}).get("document_locators", []):
        span = container.get("span", {})
        if isinstance(span.get("start"), int) and isinstance(span.get("end"), int):
            spans.append((span["start"], span["end"]))
    for container in record.get("fields", {}).get("condition_candidates", []):
        span = container.get("span", {})
        if isinstance(span.get("start"), int) and isinstance(span.get("end"), int):
            spans.append((span["start"], span["end"]))
    for measurement in record.get("fields", {}).get("mobilities", []):
        for evidence_field in (
            "span", "quantity_label", "mobility_relation", "measurement_regime",
            "temperature_evidence", "direction_evidence", "carrier_evidence",
        ):
            container = measurement.get(evidence_field, {})
            span = container if evidence_field == "span" else container.get("span", {})
            if isinstance(span.get("start"), int) and isinstance(span.get("end"), int):
                spans.append((span["start"], span["end"]))
        for evidence_list_field in (
            "method_evidence", "algorithm_evidence", "analysis_model_evidence",
            "source_relation_evidence", "document_locators", "condition_records",
        ):
            for container in measurement.get(evidence_list_field, []):
                span = container.get("span", {})
                if isinstance(span.get("start"), int) and isinstance(span.get("end"), int):
                    spans.append((span["start"], span["end"]))
    spans.sort()
    cursor = 0
    fragments = []
    for start, end in spans:
        if start < cursor or end > len(text):
            continue
        fragments.append(escape(text[cursor:start]))
        fragments.append("<mark>{}</mark>".format(escape(text[start:end])))
        cursor = end
    fragments.append(escape(text[cursor:]))
    return "".join(fragments)


def _render_measurement(measurement: dict[str, Any]) -> str:
    method_values = (
        measurement.get("methods", [])
        + measurement.get("algorithms", [])
        + measurement.get("analysis_models", [])
    )
    context = [
        measurement.get("quantity_kind"),
        measurement.get("mobility_relation", {}).get("relation"),
        measurement.get("measurement_regime", {}).get("regime"),
        measurement.get("carrier"),
        measurement.get("temperature"),
        measurement.get("direction"),
    ]
    flags = [measurement.get("review_status")] + measurement.get("review_flags", [])
    flags = [flag for flag in flags if flag]
    return """
      <tr>
        <td><strong>{value}</strong><br><span class="raw">raw: {raw}</span></td>
        <td>{context}</td>
        <td>{determination}<br><span class="raw">{relation}</span></td>
        <td>{methods}</td>
        <td>{citations}</td>
        <td>{flags}</td>
      </tr>
    """.format(
        value=escape(_measurement_value(measurement)),
        raw=escape("{} {}".format(measurement.get("raw_value", ""), measurement.get("raw_units", "")).strip()),
        context=_badge_list([value for value in context if value]),
        determination=escape(measurement.get("determination", "unspecified")),
        relation=escape(measurement.get("source_relation", "unspecified")),
        methods=_badge_list(method_values),
        citations=_badge_list(measurement.get("citation_markers", [])),
        flags=_badge_list(flags),
    )


def _render_record(record: dict[str, Any], index: int) -> str:
    fields = record.get("fields", {})
    materials = _materials(record)
    source = record.get("source", {})
    measurements = fields.get("mobilities", [])
    methods = [item.get("method") for item in fields.get("measurement_methods", []) if item.get("method")]
    algorithms = [item.get("algorithm") for item in fields.get("computational_algorithms", []) if item.get("algorithm")]
    analysis_models = [item.get("model") for item in fields.get("analysis_models", []) if item.get("model")]
    review_terms = [
        term
        for measurement in measurements
        for term in (
            [measurement.get("review_status")]
            + measurement.get("review_status_reasons", [])
            + measurement.get("review_flags", [])
        )
        if term
    ]
    search_text = " ".join(
        materials
        + methods
        + algorithms
        + analysis_models
        + review_terms
        + [record.get("evidence_text", ""), source.get("id", "")]
    ).lower()
    rows = "".join(_render_measurement(measurement) for measurement in measurements)
    if not rows:
        rows = '<tr><td colspan="6" class="muted">Method or algorithm mention only; no normalized value was found.</td></tr>'
    return """
    <article class="record" data-search="{search}">
      <header><div><span class="eyebrow">Record {index}</span><h2>{title}</h2><p class="source">{source}</p></div><span class="count">{count} value(s)</span></header>
      <div class="method-strip"><strong>Paragraph methods/models:</strong> {methods} {algorithms} {analysis_models}</div>
      <div class="table-wrap"><table>
        <thead><tr><th>Mobility</th><th>Carrier / condition</th><th>Determination / source</th><th>Method / algorithm</th><th>Citation marker</th><th>Review flags</th></tr></thead>
        <tbody>{rows}</tbody>
      </table></div>
      <details open><summary>Evidence</summary><p class="evidence">{evidence}</p></details>
    </article>
    """.format(
        search=escape(search_text),
        index=index,
        title=escape("; ".join(materials) if materials else "Unresolved material"),
        source=escape(_plain(source.get("id", "unknown source"))),
        count=len(measurements),
        methods=_badge_list(methods),
        algorithms=_badge_list(algorithms),
        analysis_models=_badge_list(analysis_models),
        rows=rows,
        evidence=_highlight_evidence(record),
    )


def render_html_report(records: Iterable[dict[str, Any]], title: str = "Mobility Miner Review Report", jsonl_path: Path | None = None) -> str:
    """Render searchable mobility records as a self-contained HTML page."""
    records = list(records)
    measurements = [measurement for record in records for measurement in record.get("fields", {}).get("mobilities", [])]
    source_count = len({record.get("source", {}).get("id", "unknown") for record in records})
    experimental = sum(1 for item in measurements if item.get("determination") == "experimental")
    computational = sum(1 for item in measurements if item.get("determination") == "computational")
    statuses = [
        item.get("review_status")
        or ("REVIEW" if item.get("review_flags") else "READY")
        for item in measurements
    ]
    ready = statuses.count("READY")
    review = statuses.count("REVIEW")
    blocked = statuses.count("BLOCKED")
    record_html = "".join(_render_record(record, index) for index, record in enumerate(records, 1))
    if not record_html:
        record_html = '<p class="empty">No mobility evidence records were extracted.</p>'
    output_note = ""
    if jsonl_path:
        output_note = "<p>JSONL: <code>{}</code></p>".format(escape(str(jsonl_path)))
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
:root{{--ink:#1e2933;--muted:#687783;--line:#d7e0e7;--paper:#fff;--surface:#f4f7f9;--accent:#315e7d;--soft:#e3eef5;--warn:#854d0e}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--surface);color:var(--ink);font:14px/1.45 Arial,sans-serif}}
.hero{{padding:26px clamp(16px,4vw,46px);background:var(--paper);border-bottom:1px solid var(--line)}}h1{{margin:0 0 6px}}.metrics{{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}}.metric{{padding:9px 12px;border:1px solid var(--line);border-radius:8px}}.metric strong{{font-size:20px;display:block}}
.toolbar{{position:sticky;top:0;padding:12px clamp(16px,4vw,46px);background:#f4f7f9ee;border-bottom:1px solid var(--line)}}input{{width:min(680px,100%);padding:9px;border:1px solid var(--line);border-radius:6px}}
main{{padding:18px clamp(16px,4vw,46px) 48px}}.record{{background:var(--paper);border:1px solid var(--line);border-radius:9px;padding:16px;margin-bottom:16px}}.record header{{display:flex;justify-content:space-between;gap:12px}}h2{{margin:3px 0;font-size:20px}}.source,.raw,.muted{{color:var(--muted)}}.eyebrow{{font-size:11px;color:var(--accent);font-weight:bold;text-transform:uppercase}}.count,.badge{{display:inline-block;border-radius:999px;padding:3px 7px;background:var(--soft);margin:2px 4px 2px 0}}.method-strip{{margin:10px 0}}.table-wrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;min-width:920px}}th,td{{border-top:1px solid var(--line);padding:9px;text-align:left;vertical-align:top}}th{{color:var(--muted)}}details{{margin-top:10px}}.evidence{{border-left:3px solid var(--accent);padding:10px;background:#f8fafb}}mark{{background:#ffe7a3}}.empty{{color:var(--muted)}}
</style></head><body><section class="hero"><h1>{title}</h1><p>Evidence-linked charge-carrier mobility values, methods, algorithms, and source relations.</p>{output_note}
<div class="metrics"><span class="metric"><strong>{records_count}</strong>records</span><span class="metric"><strong>{measurement_count}</strong>values</span><span class="metric"><strong>{source_count}</strong>sources</span><span class="metric"><strong>{experimental}</strong>experimental</span><span class="metric"><strong>{computational}</strong>computational</span><span class="metric"><strong>{ready}</strong>ready</span><span class="metric"><strong>{review}</strong>review</span><span class="metric"><strong>{blocked}</strong>blocked</span></div></section>
<section class="toolbar"><input id="search" type="search" placeholder="Search material, method, source, or evidence"></section><main>{records}</main>
<script>const q=document.getElementById('search'),rs=[...document.querySelectorAll('.record')];q.addEventListener('input',()=>{{const v=q.value.trim().toLowerCase();for(const r of rs)r.hidden=v&&!r.dataset.search.includes(v)}});</script></body></html>""".format(
        title=escape(title), output_note=output_note, records_count=len(records), measurement_count=len(measurements), source_count=source_count,
        experimental=experimental, computational=computational,
        ready=ready, review=review, blocked=blocked, records=record_html,
    )


def write_html_report(records: Iterable[dict[str, Any]], output: Path, jsonl_path: Path | None = None) -> None:
    """Write a standalone review report."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html_report(records, jsonl_path=jsonl_path), encoding="utf-8")
