"""JSON vs Markdown response shaping for tools (MCP dual format).

Pure presentation: does not query the database. Domain logic stays in `services/`.
"""

from __future__ import annotations

from typing import Any

from ssa_alj_mcp.models import ResponseFormat


def ensure_notes(payload: dict[str, Any], *extra: str) -> dict[str, Any]:
    """Guarantee a `notes` list on successful payloads (errors keep their own shape)."""
    if "error" in payload:
        return payload
    notes = list(payload.get("notes") or [])
    for n in extra:
        if n and n not in notes:
            notes.append(n)
    out = dict(payload)
    out["notes"] = notes
    return out


def format_response(
    payload: dict[str, Any],
    response_format: ResponseFormat | str = ResponseFormat.JSON,
    *,
    title: str | None = None,
) -> dict[str, Any] | str:
    """Return the dict unchanged for JSON, or a Markdown summary for MARKDOWN."""
    if isinstance(response_format, str):
        response_format = ResponseFormat(response_format)
    if response_format is ResponseFormat.JSON:
        return payload
    return to_markdown(payload, title=title)


def to_markdown(payload: dict[str, Any], *, title: str | None = None) -> str:
    if "error" in payload:
        lines = [f"**Error:** {payload['error']}"]
        if payload.get("hint"):
            lines.append(f"_Hint:_ {payload['hint']}")
        if payload.get("candidates"):
            lines.append("Candidates: " + ", ".join(str(c) for c in payload["candidates"][:12]))
        return "\n".join(lines)

    lines: list[str] = []
    if title:
        lines += [f"# {title}", ""]

    snap = payload.get("snapshot") or payload.get("report")
    if isinstance(snap, dict) and snap.get("period_end"):
        fy = snap.get("fiscal_year", "")
        lines.append(
            f"_As of {snap['period_end']}_ (FY{fy}, {snap.get('report') or snap.get('label') or ''})."
        )
        lines.append("")

    if "coverage" in payload and isinstance(payload["coverage"], dict):
        c = payload["coverage"]
        years = c.get("fiscal_years") or []
        lines.append(f"Coverage: FY{years[0]}–FY{years[-1]}" if years else "Coverage: (none)")
        if c.get("latest_period_end"):
            lines.append(f"Latest period end: `{c['latest_period_end']}`")
        lines.append("")

    items = payload.get("items")
    if items is None and "series" in payload:
        items = payload["series"]
    if items is None and "periods" in payload:
        items = payload["periods"]
    if items is None and "fiscal_years" in payload and isinstance(payload["fiscal_years"], list):
        items = payload["fiscal_years"]
    if items is None and "fiscal_year_final_snapshots" in payload:
        items = payload["fiscal_year_final_snapshots"]

    if isinstance(items, list) and items:
        total = payload.get("total", len(items))
        lines.append(f"Showing {len(items)} of {total}.")
        lines.append("")
        for row in items[:25]:
            lines.append(f"- {_row_line(row)}")
        if len(items) > 25:
            lines.append(f"- … {len(items) - 25} more")
        lines.append("")

    for key in ("judge", "office", "entity", "name", "summary", "highlights"):
        if key in payload and isinstance(payload[key], (dict, str, int)):
            lines.append(f"**{key}:** {_inline(payload[key])}")
    if "change" in payload and isinstance(payload["change"], dict):
        lines.append(f"**change:** {_inline(payload['change'])}")

    notes = payload.get("notes") or []
    if notes:
        lines.append("")
        lines.append("Notes:")
        for n in notes:
            lines.append(f"- {n}")
    return "\n".join(lines).strip() + "\n"


def _inline(value: Any) -> str:
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            if k.startswith("_"):
                continue
            parts.append(f"{k}={v}")
        return ", ".join(parts[:8])
    return str(value)


def _row_line(row: Any) -> str:
    if not isinstance(row, dict):
        return str(row)
    label = (
        row.get("office")
        or row.get("judge")
        or row.get("name")
        or row.get("unit")
        or row.get("period_end")
        or row.get("report")
        or row.get("fiscal_year")
    )
    bits = []
    if label is not None:
        bits.append(f"**{label}**")
    for k in (
        "allowance_rate",
        "total_decisions",
        "total_dispositions",
        "judges",
        "z_score",
        "gap_pts",
        "dispositions_in_period",
        "dispositions_per_day",
        "rank",
        "fiscal_year",
        "region",
    ):
        if k in row and row[k] is not None:
            bits.append(f"{k}={row[k]}")
    return " · ".join(bits) if bits else _inline(row)
