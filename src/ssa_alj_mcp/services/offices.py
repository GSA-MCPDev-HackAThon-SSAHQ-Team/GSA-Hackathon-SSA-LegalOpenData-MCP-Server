"""Hearing-office queries: name folding, compare, profile, National Ranking."""

from __future__ import annotations

import re
from typing import Any

from ssa_alj_mcp.db import query
from ssa_alj_mcp.services.common import (
    CUMULATIVE_NOTE,
    RATE_NOTE,
    enrich,
    handled,
    in_clause,
    normalize_region,
    resolve_snapshot,
    snapshot_ref,
)
from ssa_alj_mcp.services.sql import SUM_COLUMNS
from ssa_alj_mcp.utils import error, normalize_key, paginate

_SORT_KEYS = {
    "allowance_rate",
    "denial_rate",
    "total_decisions",
    "total_dispositions",
    "judges",
    "dispositions_per_judge",
}


def office_base(name: str) -> str:
    """Fold published office labels to a city-level base name for cross-year matching.

    Examples: 'LOS ANGELES (DT), CA' / 'MIAMI OHO' / 'TOLEDO OH' -> city-level base.
    """
    base = name.upper().split(",")[0]
    base = re.sub(r"\([^)]*\)", "", base)
    base = re.sub(r"\s+(OHO|OH)$", "", base)
    return re.sub(r"\s+", " ", base).strip()


def _all_offices() -> list[dict[str, Any]]:
    return query("SELECT office_id, office_name FROM hearing_office ORDER BY office_name")


def office_ids_matching(text: str) -> list[int]:
    """Return office_ids whose names contain every whitespace-separated token of `text`."""
    tokens = normalize_key(text).split()
    if not tokens:
        return []
    return [
        o["office_id"]
        for o in _all_offices()
        if set(tokens) <= set(normalize_key(o["office_name"]).split())
    ]


def office_groups_matching(text: str) -> dict[str, list[dict[str, Any]]]:
    """Map office_base -> [{office_id, office_name}, ...] for offices matching `text`."""
    groups: dict[str, list[dict[str, Any]]] = {}
    wanted = set(office_ids_matching(text))
    for o in _all_offices():
        if o["office_id"] in wanted:
            groups.setdefault(office_base(o["office_name"]), []).append(o)
    return groups


@handled
def compare_offices(
    fiscal_year: int | None = None,
    as_of: str | None = None,
    region: str | None = None,
    min_decisions: int = 0,
    sort_by: str = "allowance_rate",
    descending: bool = True,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """List offices for one snapshot ranked by a disposition measure.

    Inputs: FY or as_of, optional region/min_decisions/sort/pagination.
    Output: paginated office rows with `snapshot` and rate notes.
    """
    if sort_by not in _SORT_KEYS:
        return error(f"Unknown sort_by '{sort_by}'.", f"Use one of: {sorted(_SORT_KEYS)}")
    snap, err = resolve_snapshot(fiscal_year, as_of)
    if err:
        return err
    clauses = ["d.snapshot_id = ?", "d.office_id IS NOT NULL"]
    params: list[Any] = [snap["snapshot_id"]]
    region = normalize_region(region)
    if region:
        clauses.append("d.region_code = ?")
        params.append(region)
    rows = query(
        f"SELECT o.office_name AS office, d.region_code AS region, COUNT(DISTINCT d.alj_id) AS judges, "
        f"{SUM_COLUMNS} FROM alj_disposition d JOIN hearing_office o ON o.office_id = d.office_id "
        f"WHERE {' AND '.join(clauses)} GROUP BY d.office_id, d.region_code",
        params,
    )
    items = []
    for r in rows:
        if (r["total_decisions"] or 0) < min_decisions:
            continue
        e = enrich(r)
        e["dispositions_per_judge"] = (
            round(r["total_dispositions"] / r["judges"], 1) if r["judges"] else None
        )
        items.append(e)
    items.sort(
        key=lambda e: (
            e.get(sort_by) is None,
            -(e.get(sort_by) or 0) if descending else (e.get(sort_by) or 0),
            e["office"],
        )
    )
    result = paginate(items, limit, offset)
    result["snapshot"] = snapshot_ref(snap)
    result["filters"] = {
        "region": region,
        "min_decisions": min_decisions,
        "sort_by": sort_by,
        "descending": descending,
    }
    result["notes"] = [CUMULATIVE_NOTE, RATE_NOTE]
    return result


@handled
def get_office_profile(
    office: str, fiscal_year: int | None = None, judge_limit: int = 50
) -> dict[str, Any]:
    """Return FY trend (and optional judge roster) for one hearing office.

    Inputs: office name fragment, optional FY and judge page size.
    Output: `{office, published_names_combined, fiscal_years, judges?, notes}`.
    """
    groups = office_groups_matching(office)
    if not groups:
        return error(
            f"No hearing office matches '{office}'.",
            "Use ssa_alj_compare_offices to list office names.",
        )
    other_matches: list[str] = []
    if len(groups) > 1:
        wanted = normalize_key(office)
        exact = [b for b in groups if normalize_key(b) == wanted]
        if len(exact) == 1:
            other_matches = sorted(b for b in groups if b != exact[0])
            groups = {exact[0]: groups[exact[0]]}
        else:
            return error(
                f"'{office}' matches {len(groups)} different offices; be more specific.",
                "Repeat the call with one of the candidates.",
                candidates=sorted(groups),
            )
    base, offices = next(iter(groups.items()))
    ids = [o["office_id"] for o in offices]
    clauses = [f"d.office_id IN ({in_clause(ids)})"]
    params: list[Any] = list(ids)
    if fiscal_year is not None:
        clauses.append("s.fiscal_year = ?")
        params.append(fiscal_year)
    where = " AND ".join(clauses)

    trend_rows = query(
        "SELECT s.fiscal_year AS fiscal_year, s.reporting_period_end AS as_of, "
        f"COUNT(DISTINCT d.alj_id) AS judges, {SUM_COLUMNS} "
        "FROM alj_disposition d JOIN v_fy_final_snapshot s ON s.snapshot_id = d.snapshot_id "
        f"WHERE {where} GROUP BY s.fiscal_year ORDER BY s.fiscal_year",
        params,
    )
    if not trend_rows:
        return error(
            f"{base} has no data" + (f" for fiscal year {fiscal_year}." if fiscal_year else "."),
            "Omit fiscal_year to see the years in which the office appears.",
        )
    result: dict[str, Any] = {
        "office": base,
        "published_names_combined": [o["office_name"] for o in offices],
        "fiscal_years": [enrich(r) for r in trend_rows],
    }
    if fiscal_year is not None:
        judge_rows = query(
            f"SELECT a.name_raw AS judge, {SUM_COLUMNS} FROM alj_disposition d "
            "JOIN alj a ON a.alj_id = d.alj_id JOIN v_fy_final_snapshot s ON s.snapshot_id = d.snapshot_id "
            f"WHERE {where} GROUP BY d.alj_id ORDER BY SUM(d.total_dispositions) DESC",
            params,
        )
        judges = [enrich(r) for r in judge_rows]
        result["judges"] = paginate(judges, judge_limit, 0)
    if other_matches:
        result["other_matching_offices"] = other_matches
    result["notes"] = [
        CUMULATIVE_NOTE,
        RATE_NOTE,
        "Office names change over time; the 'published_names_combined' variants were merged by city name (best effort).",
    ]
    return result


@handled
def office_processing_ranking(
    period_end: str | None = None,
    region: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """Return SSA's published National Ranking rows for one ranking snapshot.

    Inputs: optional period_end and region; pagination.
    Output: paginated ranking rows with `snapshot` pointing at the ranking report.
    """
    snaps = query(
        "SELECT snapshot_id, fiscal_year, reporting_period_end, report_label FROM report_snapshot "
        "WHERE report_kind = 'office_ranking' ORDER BY reporting_period_end DESC"
    )
    if not snaps:
        return error("The database contains no National Ranking reports.", "Run the load script.")
    if period_end:
        snap = next((s for s in snaps if s["reporting_period_end"] == period_end), None)
        if snap is None:
            return error(
                f"No ranking report ends on {period_end}.",
                f"Available period ends: {[s['reporting_period_end'] for s in snaps]}",
            )
    else:
        snap = snaps[0]
    clauses, params = ["r.snapshot_id = ?"], [snap["snapshot_id"]]
    region = normalize_region(region)
    if region:
        clauses.append("r.region_code = ?")
        params.append(region)
    rows = query(
        "SELECT r.rank AS rank, o.office_name AS office, r.region_code AS region, "
        "r.alj_dispositions_per_day AS dispositions_per_day_per_alj, r.workdays AS workdays "
        "FROM office_ranking r JOIN hearing_office o ON o.office_id = r.office_id "
        f"WHERE {' AND '.join(clauses)} ORDER BY r.rank, o.office_name",
        params,
    )
    result = paginate(rows, limit, offset)
    result["snapshot"] = snapshot_ref(snap)
    result["notes"] = [
        "Rank 1 = most dispositions per day per ALJ. This is SSA's separately published "
        "National Ranking report, not derived from the judge-level files."
    ]
    return result
