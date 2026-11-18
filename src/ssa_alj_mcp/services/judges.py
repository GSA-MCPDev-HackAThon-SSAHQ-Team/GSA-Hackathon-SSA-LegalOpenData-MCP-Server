"""Judge-level queries.

SSA publishes no judge identifier, so a judge is identified by published name. Spelling variants
that differ only in case/punctuation (e.g. 'Akins, George M' / 'Akins, George M.') are grouped by
`alj.name_key`. Two different people with the same name cannot be told apart; the profile flags
that when one office lists the same name more than once in a snapshot.
"""

from __future__ import annotations

from typing import Any

from ssa_alj_mcp.db import query
from ssa_alj_mcp.services.common import (
    CUMULATIVE_NOTE,
    RATE_NOTE,
    enrich,
    handled,
    in_clause,
)
from ssa_alj_mcp.services.offices import office_ids_matching
from ssa_alj_mcp.services.sql import SUM_COLUMNS
from ssa_alj_mcp.utils import error, normalize_key, paginate, rate

IDENTITY_NOTE = (
    "SSA publishes no judge ID; judges are matched by published name (case/punctuation folded). "
    "Namesakes cannot be distinguished."
)


def _name_groups(name: str) -> list[dict[str, Any]]:
    """Judges matching `name`, grouped by name_key. Exact key match wins, else all-words match."""
    key = normalize_key(name)
    if not key:
        return []
    rows = query("SELECT alj_id, name_raw, name_key FROM alj WHERE name_key = ?", (key,))
    if not rows:
        tokens = key.split()
        where = " AND ".join("(' ' || name_key || ' ') LIKE ?" for _ in tokens)
        rows = query(
            f"SELECT alj_id, name_raw, name_key FROM alj WHERE {where}",
            [f"% {t} %" for t in tokens],
        )
    groups: dict[str, dict[str, Any]] = {}
    for r in rows:
        g = groups.setdefault(
            r["name_key"], {"name_key": r["name_key"], "alj_ids": [], "names": []}
        )
        g["alj_ids"].append(r["alj_id"])
        g["names"].append(r["name_raw"])
    return sorted(groups.values(), key=lambda g: g["name_key"])


def _display_name(names: list[str]) -> str:
    return sorted(names, key=lambda n: (n.endswith("."), n))[0]


@handled
def search_judges(
    name: str,
    office: str | None = None,
    fiscal_year: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Search published judge names; returns a paginated list of matches.

    Inputs: name fragment, optional office/FY filters and pagination.
    Output: standard page envelope of judge summaries plus identity notes.
    """
    groups = _name_groups(name)
    if not groups:
        return {
            "total": 0,
            "count": 0,
            "offset": 0,
            "has_more": False,
            "next_offset": None,
            "items": [],
            "notes": [
                "No judge matched. Try fewer words or just the last name; matching ignores case and punctuation.",
                IDENTITY_NOTE,
            ],
        }

    office_ids: list[int] | None = None
    if office:
        office_ids = office_ids_matching(office)
        if not office_ids:
            return error(
                f"No hearing office matches '{office}'.",
                "Use ssa_alj_compare_offices to list office names.",
            )

    all_ids = [i for g in groups for i in g["alj_ids"]]
    clauses = [f"d.alj_id IN ({in_clause(all_ids)})"]
    params: list[Any] = list(all_ids)
    if office_ids is not None:
        clauses.append(f"d.office_id IN ({in_clause(office_ids)})")
        params += office_ids
    if fiscal_year is not None:
        clauses.append("s.fiscal_year = ?")
        params.append(fiscal_year)
    coverage = query(
        "SELECT a.name_key AS name_key, s.fiscal_year AS fiscal_year, o.office_name AS office "
        "FROM alj_disposition d JOIN alj a ON a.alj_id = d.alj_id "
        "JOIN v_fy_final_snapshot s ON s.snapshot_id = d.snapshot_id "
        "LEFT JOIN hearing_office o ON o.office_id = d.office_id "
        f"WHERE {' AND '.join(clauses)} ORDER BY s.fiscal_year",
        params,
    )
    by_key: dict[str, list[dict[str, Any]]] = {}
    for c in coverage:
        by_key.setdefault(c["name_key"], []).append(c)

    items = []
    for g in groups:
        rows = by_key.get(g["name_key"])
        if (office_ids is not None or fiscal_year is not None) and not rows:
            continue
        rows = rows or []
        years = sorted({r["fiscal_year"] for r in rows})
        latest_offices = sorted(
            {
                r["office"]
                for r in rows
                if r["fiscal_year"] == (years[-1] if years else None) and r["office"]
            }
        )
        items.append(
            {
                "name": _display_name(g["names"]),
                "name_variants": sorted(set(g["names"])),
                "fiscal_years": years,
                "latest_fiscal_year": years[-1] if years else None,
                "offices_in_latest_fiscal_year": latest_offices,
            }
        )
    result = paginate(items, limit, offset)
    result["notes"] = [
        IDENTITY_NOTE,
        "fiscal_years lists fiscal years with a final-snapshot row for the judge.",
    ]
    return result


def _national_rates() -> dict[int, float | None]:
    rows = query(
        f"SELECT s.fiscal_year AS fiscal_year, {SUM_COLUMNS} FROM alj_disposition d "
        "JOIN v_fy_final_snapshot s ON s.snapshot_id = d.snapshot_id GROUP BY s.fiscal_year"
    )
    return {r["fiscal_year"]: rate(r["total_awards"], r["total_decisions"]) for r in rows}


@handled
def get_judge_profile(name: str, fiscal_year: int | None = None) -> dict[str, Any]:
    """Profile one judge across fiscal years with national rate comparison.

    Inputs: published name (and optional FY). Output: identity, FY series, notes.
    """

    groups = _name_groups(name)
    if not groups:
        return error(
            f"No judge matches '{name}'.", "Use ssa_alj_search_judges to find the published name."
        )
    if len(groups) > 1:
        return error(
            f"'{name}' matches {len(groups)} different judges; be more specific.",
            "Repeat the call with one of the candidate names.",
            candidates=[_display_name(g["names"]) for g in groups[:15]],
            candidate_count=len(groups),
        )
    group = groups[0]
    ids = group["alj_ids"]
    clauses = [f"d.alj_id IN ({in_clause(ids)})"]
    params: list[Any] = list(ids)
    if fiscal_year is not None:
        clauses.append("s.fiscal_year = ?")
        params.append(fiscal_year)
    where = " AND ".join(clauses)

    trend_rows = query(
        f"SELECT s.fiscal_year AS fiscal_year, s.reporting_period_end AS as_of, "
        f"COUNT(*) AS rows_published, COUNT(DISTINCT d.office_id) AS offices, {SUM_COLUMNS} "
        "FROM alj_disposition d JOIN v_fy_final_snapshot s ON s.snapshot_id = d.snapshot_id "
        f"WHERE {where} GROUP BY s.fiscal_year ORDER BY s.fiscal_year",
        params,
    )
    if not trend_rows:
        return error(
            f"{_display_name(group['names'])} has no data"
            + (f" for fiscal year {fiscal_year}." if fiscal_year else "."),
            "Omit fiscal_year to see the fiscal years in which the judge appears.",
        )
    national = _national_rates()
    trend = []
    for r in trend_rows:
        e = enrich(r)
        e["national_allowance_rate"] = national.get(r["fiscal_year"])
        trend.append(e)

    notes = [CUMULATIVE_NOTE, RATE_NOTE, IDENTITY_NOTE]
    result: dict[str, Any] = {
        "judge": {
            "name": _display_name(group["names"]),
            "name_variants": sorted(set(group["names"])),
        },
        "fiscal_years": trend,
    }

    if fiscal_year is not None:
        office_rows = query(
            f"SELECT o.office_name AS office, d.region_code AS region, COUNT(*) AS rows_published, "
            f"{SUM_COLUMNS} FROM alj_disposition d JOIN v_fy_final_snapshot s ON s.snapshot_id = d.snapshot_id "
            f"LEFT JOIN hearing_office o ON o.office_id = d.office_id WHERE {where} "
            "GROUP BY d.office_id, d.region_code ORDER BY SUM(d.total_dispositions) DESC",
            params,
        )
        result["by_office"] = [enrich(r) for r in office_rows]
        if any(r["rows_published"] > 1 for r in office_rows):
            notes.append(
                "At least one office lists this name more than once in the snapshot; these may be two "
                "judges with the same name, and their counts are summed here."
            )
    result["notes"] = notes
    return result
