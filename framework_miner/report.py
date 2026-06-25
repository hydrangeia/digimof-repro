"""HTML review reports for extracted framework records."""

from __future__ import annotations

from collections import Counter
from html import escape
from pathlib import Path
from typing import Any, Iterable


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

FIELD_GROUPS = [
    ("Identity", ["names", "synthesis_routes", "polymerization_routes", "linkages", "topologies"]),
    ("Building Blocks", ["monomers", "linker_routes"]),
    ("Conditions", ["catalysts", "bases", "solvents", "atmospheres", "interfaces", "substrates", "temperature", "time"]),
]

SYNTHESIS_SIGNAL_FIELDS = {
    "synthesis_routes",
    "polymerization_routes",
    "temperature",
    "time",
    "solvents",
    "catalysts",
    "bases",
    "atmospheres",
    "interfaces",
    "substrates",
}


def _plain_text(value: Any) -> str:
    return " ".join(str(value).split())


def field_values(fields: dict[str, Any], field_name: str) -> list[str]:
    """Return human-readable values for a normalized field."""
    values = fields.get(field_name, [])
    if not isinstance(values, list):
        return []

    extracted: list[str] = []
    value_key = FIELD_VALUE_KEYS.get(field_name)
    for value in values:
        text = ""
        if isinstance(value, str):
            text = value
        elif isinstance(value, dict) and value_key:
            raw_value = value.get(value_key)
            if isinstance(raw_value, str):
                text = raw_value
                role = value.get("role")
                if isinstance(role, str) and role:
                    text = "{} ({})".format(text, role)
        if text:
            text = _plain_text(text)
            if text not in extracted:
                extracted.append(text)
    return extracted


def record_evidence(record: dict[str, Any]) -> list[str]:
    evidence = record.get("evidence_texts")
    if isinstance(evidence, list):
        return [_plain_text(item) for item in evidence if isinstance(item, str) and item.strip()]
    evidence_text = record.get("evidence_text")
    if isinstance(evidence_text, str) and evidence_text.strip():
        return [_plain_text(evidence_text)]
    return []


def record_review_label(record: dict[str, Any]) -> str:
    fields = record.get("fields", {})
    names = field_values(fields, "names")
    has_synthesis_signal = any(field_values(fields, field_name) for field_name in SYNTHESIS_SIGNAL_FIELDS)
    if names and has_synthesis_signal:
        return "Likely synthesis record"
    if names:
        return "Named framework, sparse conditions"
    if has_synthesis_signal:
        return "Condition evidence, no name"
    return "Needs review"


def record_review_notes(record: dict[str, Any]) -> list[str]:
    fields = record.get("fields", {})
    notes: list[str] = []
    if not field_values(fields, "names"):
        notes.append("No explicit framework name was extracted.")
    if len(record_evidence(record)) > 1:
        notes.append("Merged from multiple evidence snippets; review for non-synthesis leakage.")
    if not any(field_values(fields, field_name) for field_name in SYNTHESIS_SIGNAL_FIELDS):
        notes.append("No synthesis-condition field was extracted.")
    return notes


def summarize_records(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    records = list(records)
    framework_counts = Counter(record.get("framework_type", "unknown") for record in records)
    source_counts = Counter(record.get("source", {}).get("id", "unknown") for record in records)
    named_count = sum(1 for record in records if field_values(record.get("fields", {}), "names"))
    condition_count = sum(
        1
        for record in records
        if any(field_values(record.get("fields", {}), field_name) for field_name in SYNTHESIS_SIGNAL_FIELDS)
    )
    return {
        "total": len(records),
        "framework_counts": dict(framework_counts),
        "source_count": len(source_counts),
        "named_count": named_count,
        "condition_count": condition_count,
    }


def _render_badges(values: list[str], css_class: str = "badge") -> str:
    if not values:
        return '<span class="muted">-</span>'
    return "".join('<span class="{}">{}</span>'.format(css_class, escape(value)) for value in values)


def _render_field_group(title: str, field_names: list[str], fields: dict[str, Any]) -> str:
    rows = []
    for field_name in field_names:
        values = field_values(fields, field_name)
        if values:
            rows.append(
                "<tr><th>{}</th><td>{}</td></tr>".format(
                    escape(field_name.replace("_", " ").title()),
                    _render_badges(values),
                )
            )
    if not rows:
        return ""
    return """
    <section class="field-group">
      <h3>{}</h3>
      <table>{}</table>
    </section>
    """.format(escape(title), "\n".join(rows))


def _render_record(record: dict[str, Any], index: int) -> str:
    fields = record.get("fields", {})
    framework = _plain_text(record.get("framework_type", "unknown")).upper()
    source = record.get("source", {})
    source_id = _plain_text(source.get("id", "unknown"))
    paragraph = source.get("paragraph_index")
    paragraph_text = "" if paragraph is None else " · paragraph {}".format(escape(str(paragraph)))
    names = field_values(fields, "names")
    label = record_review_label(record)
    notes = record_review_notes(record)
    evidence = record_evidence(record)
    evidence_html = "\n".join("<p>{}</p>".format(escape(text)) for text in evidence)
    note_html = ""
    if notes:
        note_html = '<ul class="notes">{}</ul>'.format(
            "".join("<li>{}</li>".format(escape(note)) for note in notes)
        )
    groups = "\n".join(
        _render_field_group(group_title, field_names, fields)
        for group_title, field_names in FIELD_GROUPS
    )
    searchable = " ".join([framework, source_id, label] + names + evidence)
    return """
    <article class="record" data-framework="{framework}" data-search="{searchable}">
      <header class="record-header">
        <div>
          <div class="eyebrow">Record {index} · {framework}</div>
          <h2>{names}</h2>
          <p class="source">{source}{paragraph}</p>
        </div>
        <span class="status">{label}</span>
      </header>
      {notes}
      <div class="field-grid">
        {groups}
      </div>
      <details>
        <summary>Evidence snippets ({evidence_count})</summary>
        <div class="evidence">{evidence}</div>
      </details>
    </article>
    """.format(
        framework=escape(framework),
        searchable=escape(searchable.lower()),
        index=index,
        names=escape("; ".join(names) if names else "Unnamed framework candidate"),
        source=escape(source_id),
        paragraph=paragraph_text,
        label=escape(label),
        notes=note_html,
        groups=groups or '<p class="muted">No normalized fields were extracted.</p>',
        evidence_count=len(evidence),
        evidence=evidence_html or '<p class="muted">No evidence text was stored.</p>',
    )


def render_html_report(
    records: Iterable[dict[str, Any]],
    title: str = "Framework Miner Review Report",
    jsonl_path: Path | None = None,
) -> str:
    records = list(records)
    summary = summarize_records(records)
    framework_counts = summary["framework_counts"]
    jsonl_note = ""
    if jsonl_path is not None:
        jsonl_note = '<p class="jsonl">JSONL output: <code>{}</code></p>'.format(escape(str(jsonl_path)))

    record_html = "\n".join(_render_record(record, index) for index, record in enumerate(records, start=1))
    if not record_html:
        record_html = '<p class="empty">No framework records passed the selected filters.</p>'

    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1f2933;
      --muted: #687582;
      --line: #d9e1e8;
      --surface: #f7f9fb;
      --paper: #ffffff;
      --accent: #146c5c;
      --accent-soft: #dcefeb;
      --warn: #9a5b13;
      --warn-soft: #fff1d6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: var(--surface);
      line-height: 1.45;
    }}
    header.hero {{
      background: var(--paper);
      border-bottom: 1px solid var(--line);
      padding: 28px clamp(18px, 4vw, 48px);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      letter-spacing: 0;
    }}
    .subtitle, .jsonl, .source, .muted {{
      color: var(--muted);
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      margin-top: 22px;
      max-width: 980px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fbfdfe;
    }}
    .metric strong {{
      display: block;
      font-size: 24px;
      margin-bottom: 2px;
    }}
    .toolbar {{
      position: sticky;
      top: 0;
      z-index: 2;
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
      background: rgba(247, 249, 251, 0.96);
      border-bottom: 1px solid var(--line);
      padding: 12px clamp(18px, 4vw, 48px);
      backdrop-filter: blur(8px);
    }}
    input, select {{
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      background: var(--paper);
      color: var(--ink);
      font: inherit;
    }}
    input {{
      flex: 1 1 260px;
    }}
    main {{
      padding: 18px clamp(18px, 4vw, 48px) 48px;
    }}
    .record {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      margin: 0 0 16px;
      padding: 18px;
    }}
    .record-header {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      border-bottom: 1px solid var(--line);
      padding-bottom: 12px;
      margin-bottom: 14px;
    }}
    .eyebrow {{
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    h2 {{
      margin: 4px 0;
      font-size: 20px;
      letter-spacing: 0;
    }}
    .status {{
      border-radius: 999px;
      padding: 6px 10px;
      color: var(--accent);
      background: var(--accent-soft);
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .notes {{
      margin: 0 0 14px;
      padding: 10px 12px 10px 28px;
      border-radius: 8px;
      background: var(--warn-soft);
      color: var(--warn);
    }}
    .field-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 14px;
    }}
    .field-group {{
      min-width: 0;
    }}
    .field-group h3 {{
      margin: 0 0 8px;
      font-size: 14px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }}
    th, td {{
      border-top: 1px solid var(--line);
      padding: 8px 0;
      vertical-align: top;
      text-align: left;
      overflow-wrap: anywhere;
    }}
    th {{
      width: 34%;
      color: var(--muted);
      font-weight: 700;
      padding-right: 10px;
    }}
    .badge {{
      display: inline-block;
      max-width: 100%;
      margin: 0 6px 6px 0;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 8px;
      background: #fbfdfe;
      overflow-wrap: anywhere;
    }}
    details {{
      margin-top: 14px;
      border-top: 1px solid var(--line);
      padding-top: 12px;
    }}
    summary {{
      cursor: pointer;
      color: var(--accent);
      font-weight: 700;
    }}
    .evidence p {{
      background: #fbfdfe;
      border-left: 3px solid var(--accent);
      padding: 10px 12px;
      margin: 10px 0;
    }}
    .empty {{
      margin: 40px 0;
      color: var(--muted);
    }}
    @media (max-width: 700px) {{
      .record-header {{
        display: block;
      }}
      .status {{
        display: inline-block;
        margin-top: 10px;
      }}
    }}
  </style>
</head>
<body>
  <header class="hero">
    <h1>{title}</h1>
    <p class="subtitle">A local, reviewable synthesis-extraction report for MOF and COF literature.</p>
    {jsonl_note}
    <section class="summary" aria-label="Summary">
      <div class="metric"><strong>{total}</strong><span>records</span></div>
      <div class="metric"><strong>{mof}</strong><span>MOF records</span></div>
      <div class="metric"><strong>{cof}</strong><span>COF records</span></div>
      <div class="metric"><strong>{sources}</strong><span>sources</span></div>
      <div class="metric"><strong>{named}</strong><span>with names</span></div>
      <div class="metric"><strong>{conditions}</strong><span>with conditions</span></div>
    </section>
  </header>
  <section class="toolbar" aria-label="Filters">
    <input id="search" type="search" placeholder="Search names, fields, evidence, source">
    <select id="framework">
      <option value="all">All frameworks</option>
      <option value="MOF">MOF only</option>
      <option value="COF">COF only</option>
    </select>
  </section>
  <main id="records">
    {records}
  </main>
  <script>
    const search = document.getElementById('search');
    const framework = document.getElementById('framework');
    const records = Array.from(document.querySelectorAll('.record'));
    function applyFilters() {{
      const query = search.value.trim().toLowerCase();
      const selected = framework.value;
      for (const record of records) {{
        const frameworkMatch = selected === 'all' || record.dataset.framework === selected;
        const queryMatch = !query || record.dataset.search.includes(query);
        record.hidden = !(frameworkMatch && queryMatch);
      }}
    }}
    search.addEventListener('input', applyFilters);
    framework.addEventListener('change', applyFilters);
  </script>
</body>
</html>
""".format(
        title=escape(title),
        jsonl_note=jsonl_note,
        total=summary["total"],
        mof=framework_counts.get("MOF", 0),
        cof=framework_counts.get("COF", 0),
        sources=summary["source_count"],
        named=summary["named_count"],
        conditions=summary["condition_count"],
        records=record_html,
    )


def write_html_report(
    records: Iterable[dict[str, Any]],
    output: Path,
    title: str = "Framework Miner Review Report",
    jsonl_path: Path | None = None,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html_report(records, title=title, jsonl_path=jsonl_path), encoding="utf-8")
