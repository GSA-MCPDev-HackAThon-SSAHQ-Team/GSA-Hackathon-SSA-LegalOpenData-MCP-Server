"""Discovery helpers: curated business questions and SSA source URLs for verification."""

from __future__ import annotations

import re
from typing import Any

from ssa_alj_mcp.db import query
from ssa_alj_mcp.guardrails import scope_note
from ssa_alj_mcp.services.common import CUMULATIVE_NOTE, RATE_NOTE, handled
from ssa_alj_mcp.utils import error, paginate

DATASETS_INDEX = "https://www.ssa.gov/appeals/DataSets/"
DATAGOV_COLLECTION = "US-GOV-SSA-1199"

_REPORT_KINDS = {
    "disposition": "alj_disposition",
    "ranking": "office_ranking",
}

# Curated questions an analyst (or agent) can pick. Each entry names the tools to call —
# this is a recipe catalog, not a free-form SQL runner.
_CATALOG: list[dict[str, Any]] = [
    {
        "id": "coverage",
        "category": "coverage",
        "question": "What fiscal years and report as-of dates are loaded?",
        "tags": ["coverage", "years", "as of", "reports", "available"],
        "tools": [{"name": "ssa_alj_list_reports", "args": {}}],
        "verify_hint": f"Cross-check the public file list at {DATASETS_INDEX}",
    },
    {
        "id": "fy2024_top_allowance_office",
        "category": "offices",
        "question": (
            "Among hearing offices with at least 1,000 decisions in fiscal year 2024, "
            "which office had the highest allowance rate?"
        ),
        "tags": ["office", "allowance", "highest", "2024", "rank", "queens"],
        "tools": [
            {
                "name": "ssa_alj_compare_offices",
                "args": {
                    "fiscal_year": 2024,
                    "min_decisions": 1000,
                    "sort_by": "allowance_rate",
                    "descending": True,
                },
            },
            {
                "name": "ssa_alj_source_links",
                "args": {"fiscal_year": 2024, "report_kind": "disposition"},
            },
        ],
        "verify_hint": (
            "Open the FY2024 September disposition HTML/XML under archive/03_FY2024/ "
            "and confirm QUEENS awards ÷ decisions."
        ),
    },
    {
        "id": "fy2024_national_allowance",
        "category": "trends",
        "question": "What was the national ALJ allowance rate for fiscal year 2024?",
        "tags": ["national", "allowance", "2024", "rate"],
        "tools": [
            {
                "name": "ssa_alj_national_trend",
                "args": {
                    "group_by": "national",
                    "from_fiscal_year": 2024,
                    "to_fiscal_year": 2024,
                },
            },
            {
                "name": "ssa_alj_source_links",
                "args": {"fiscal_year": 2024, "report_kind": "disposition"},
            },
        ],
        "verify_hint": "Sum national awards and decisions from the FY2024 September disposition file.",
    },
    {
        "id": "peak_national_allowance_year",
        "category": "trends",
        "question": "In which fiscal year was the national ALJ allowance rate the highest?",
        "tags": ["national", "allowance", "highest", "trend", "peak", "2010"],
        "tools": [{"name": "ssa_alj_national_trend", "args": {"group_by": "national"}}],
        "verify_hint": "Compare September (FY-final) disposition files across years on DataSets.",
    },
    {
        "id": "miami_top_judge_fy2024",
        "category": "judges",
        "question": (
            "For Miami in fiscal year 2024, which judge had the highest allowance rate "
            "among judges with at least 100 decisions?"
        ),
        "tags": ["miami", "judge", "allowance", "2024", "within office"],
        "tools": [
            {
                "name": "ssa_alj_within_office_variation",
                "args": {"office": "Miami", "fiscal_year": 2024, "min_decisions": 100},
            },
            {
                "name": "ssa_alj_source_links",
                "args": {"fiscal_year": 2024, "report_kind": "disposition"},
            },
        ],
        "verify_hint": "Filter the FY2024 September file for Miami office rows and compare judges.",
    },
    {
        "id": "national_ranking_rank1",
        "category": "ranking",
        "question": (
            "Which hearing office is rank 1 on the latest SSA National Ranking "
            "(dispositions per day per ALJ)?"
        ),
        "tags": ["ranking", "processing", "speed", "rank 1", "ponce", "national ranking"],
        "tools": [
            {"name": "ssa_alj_office_processing_ranking", "args": {}},
            {"name": "ssa_alj_source_links", "args": {"report_kind": "ranking"}},
        ],
        "verify_hint": (
            "Open the matching 04_* Disposition Per Day Per ALJ Ranking HTML under DataSets/archive."
        ),
    },
    {
        "id": "charleston_wv_change",
        "category": "offices",
        "question": (
            "By how many percentage points did the CHARLESTON WV hearing office allowance "
            "rate change from FY2023 to FY2024?"
        ),
        "tags": ["charleston", "change", "compare", "2023", "2024", "allowance"],
        "tools": [
            {
                "name": "ssa_alj_compare_periods",
                "args": {
                    "entity": "office",
                    "fiscal_year_a": 2023,
                    "fiscal_year_b": 2024,
                    "name": "CHARLESTON WV",
                },
            },
            {
                "name": "ssa_alj_source_links",
                "args": {"fiscal_year": 2024, "report_kind": "disposition"},
            },
        ],
        "verify_hint": "Compare CHARLESTON WV rows in the FY2023 and FY2024 September disposition files.",
    },
    {
        "id": "data_gaps",
        "category": "quality",
        "question": "What gaps or out-of-scope topics should I know about before drawing conclusions?",
        "tags": ["gaps", "quality", "missing", "case mix", "bias", "wait time"],
        "tools": [{"name": "ssa_alj_data_quality_notes", "args": {}}],
        "verify_hint": "SSA DataSets describe published disposition counts only — not wait times or case mix.",
    },
    {
        "id": "monthly_pace_fy2024",
        "category": "trends",
        "question": "Is national disposition output speeding up or slowing down inside fiscal year 2024?",
        "tags": ["pace", "monthly", "2024", "speed", "within year"],
        "tools": [
            {"name": "ssa_alj_monthly_pace", "args": {"fiscal_year": 2024}},
            {
                "name": "ssa_alj_source_links",
                "args": {"fiscal_year": 2024, "report_kind": "disposition"},
            },
        ],
        "verify_hint": (
            "Compare consecutive FY2024 monthly disposition snapshots; do not sum them."
        ),
    },
    {
        "id": "judge_profile",
        "category": "judges",
        "question": "Summarise one published ALJ's year-by-year dispositions versus the national rate.",
        "tags": ["judge", "profile", "search", "name"],
        "tools": [
            {"name": "ssa_alj_search_judges", "args": {"name": "<published name fragment>"}},
            {"name": "ssa_alj_get_judge_profile", "args": {"name": "<exact published name>"}},
        ],
        "verify_hint": "Find that judge's rows in the September disposition file for each FY of interest.",
    },
]


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1}


def _score_entry(entry: dict[str, Any], tokens: set[str]) -> int:
    hay = _tokens(entry["question"] + " " + " ".join(entry.get("tags", [])))
    return len(tokens & hay)


def _catalog_items() -> list[dict[str, Any]]:
    return [
        {
            "id": e["id"],
            "category": e["category"],
            "question": e["question"],
            "tools": e["tools"],
            "verify_hint": e["verify_hint"],
        }
        for e in _CATALOG
    ]


@handled
def business_queries(
    query: str | None = None,
    category: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """Return curated analyst questions, or match a custom question to suggested tools.

    Omitting `query` lists the catalog (optionally filtered by category). Passing `query`
    ranks catalog entries by keyword overlap and returns a suggested tool plan — it does
    not execute analytics itself.
    """
    items = _catalog_items()
    if category:
        wanted = category.strip().lower()
        items = [i for i in items if i["category"] == wanted]
        if not items:
            cats = sorted({e["category"] for e in _CATALOG})
            return error(
                f"Unknown category '{category}'.",
                f"Use one of: {cats}",
            )

    notes = [
        "These are recipes (which tools to call), not computed answers. "
        "Run the named tools next, then ssa_alj_source_links to verify on ssa.gov.",
        CUMULATIVE_NOTE,
        RATE_NOTE,
    ]

    if query and query.strip():
        tokens = _tokens(query)
        ranked = sorted(
            ((_score_entry(e, tokens), e) for e in _CATALOG),
            key=lambda pair: (-pair[0], pair[1]["id"]),
        )
        matches = [
            {
                "id": e["id"],
                "category": e["category"],
                "question": e["question"],
                "score": score,
                "tools": e["tools"],
                "verify_hint": e["verify_hint"],
            }
            for score, e in ranked
            if score > 0
        ][:5]
        return {
            "mode": "custom",
            "query": query.strip(),
            "scope_note": scope_note(query),
            "matches": matches,
            "suggested_plan": matches[0]["tools"]
            if matches
            else [
                {"name": "ssa_alj_list_reports", "args": {}},
                {"name": "ssa_alj_data_quality_notes", "args": {}},
            ],
            "fallback_note": None
            if matches
            else (
                "No close catalog match. Start with list_reports / data_quality_notes, "
                "then pick a reference or analysis tool from the catalog."
            ),
            "catalog_size": len(_CATALOG),
            "notes": notes,
        }

    page = paginate(items, limit=limit, offset=offset)
    page["mode"] = "catalog"
    page["categories"] = sorted({e["category"] for e in _CATALOG})
    page["notes"] = notes
    return page


def _source_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_kind": "disposition" if row["report_kind"] == "alj_disposition" else "ranking",
        "fiscal_year": row["fiscal_year"],
        "period_end": row["reporting_period_end"],
        "report": row["report_label"],
        "is_fy_final": bool(row.get("is_fy_final")),
        "html_url": row.get("source_html_url"),
        "xml_url": row.get("source_xml_url"),
        "local_path": row.get("local_path"),
    }


@handled
def source_links(
    fiscal_year: int | None = None,
    as_of: str | None = None,
    report_kind: str = "disposition",
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """Return SSA HTML/XML URLs for disposition or National Ranking snapshots.

    Prefer `as_of` when set; otherwise FY-final for `fiscal_year`; otherwise the latest
    matching snapshot. Use `report_kind='both'` to list disposition and ranking sources.
    """
    kind = (report_kind or "disposition").strip().lower()
    if kind not in ("disposition", "ranking", "both"):
        return error(
            "report_kind must be 'disposition', 'ranking', or 'both'.",
            "Disposition = allowance/decision counts; ranking = dispositions per day per ALJ.",
        )

    kinds = list(_REPORT_KINDS.values()) if kind == "both" else [_REPORT_KINDS[kind]]

    select = (
        "SELECT report_kind, fiscal_year, reporting_period_end, report_label, "
        "source_xml_url, source_html_url, local_path, "
        "CASE WHEN snapshot_id IN (SELECT snapshot_id FROM v_fy_final_snapshot) "
        "THEN 1 ELSE 0 END AS is_fy_final "
        "FROM report_snapshot WHERE report_kind IN ({ph})"
    ).format(ph=",".join("?" for _ in kinds))
    params: list[Any] = list(kinds)

    if as_of:
        select += " AND reporting_period_end = ?"
        params.append(as_of)
    elif fiscal_year is not None:
        select += " AND fiscal_year = ?"
        params.append(fiscal_year)
        if kind in ("disposition", "both"):
            # Prefer FY-final disposition rows when a year is named without as_of.
            pass

    select += " ORDER BY reporting_period_end DESC, report_kind, snapshot_id DESC"
    rows = query(select, tuple(params))
    if not rows:
        hint = "Use ssa_alj_list_reports to see valid fiscal years and period ends."
        if as_of:
            return error(f"No snapshot ends on {as_of}.", hint)
        if fiscal_year is not None:
            return error(f"No snapshot for fiscal year {fiscal_year}.", hint)
        return error("No matching snapshots in the database.", hint)

    # When a single FY is requested for disposition (not both/as_of), surface FY-final first.
    if fiscal_year is not None and as_of is None and kind == "disposition":
        finals = [r for r in rows if r.get("is_fy_final")]
        if finals:
            rows = finals + [r for r in rows if not r.get("is_fy_final")]

    items = [_source_row(r) for r in rows]
    # Primary = first item (latest or FY-final preference above)
    primary = items[0]
    page = paginate(items, limit=limit, offset=offset)
    page["primary"] = primary
    page["datasets_index"] = DATASETS_INDEX
    page["datagov_collection"] = DATAGOV_COLLECTION
    page["notes"] = [
        "Open html_url (or xml_url) on ssa.gov to verify figures for that snapshot.",
        "Ranking and disposition reports are different SSA publications — do not mix them.",
        CUMULATIVE_NOTE,
    ]
    return page
