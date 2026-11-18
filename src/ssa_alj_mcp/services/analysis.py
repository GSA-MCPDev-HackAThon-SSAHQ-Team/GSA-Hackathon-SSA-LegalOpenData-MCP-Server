"""Peer-comparison analytics: outlier detection and within-office variation."""

from __future__ import annotations

import statistics
from typing import Any

from ssa_alj_mcp.db import query
from ssa_alj_mcp.services.common import (
    CUMULATIVE_NOTE,
    add_sums,
    handled,
    normalize_region,
    resolve_snapshot,
    snapshot_ref,
    zero_sums,
)
from ssa_alj_mcp.services.offices import office_ids_matching
from ssa_alj_mcp.services.sql import SUM_COLUMNS, SUM_FIELDS
from ssa_alj_mcp.utils import error, paginate, rate

MEASURES = ("allowance_rate", "non_decision_share", "dispositions")
CASE_MIX_NOTE = (
    "Statistical outliers only. Rates are not adjusted for case mix, region, claimant age or "
    "docket composition, and a high or low value is not evidence of error, bias or poor "
    "performance. Use as a prompt for questions, not as a conclusion."
)


def _raw_value(measure: str, s: dict[str, Any], per_judge_count: int | None) -> float | None:
    """Compute the selected measure from a sum row (optionally per-judge for offices)."""
    dec, disp, awards = s["total_decisions"], s["total_dispositions"], s["total_awards"]
    if measure == "allowance_rate":
        return awards / dec if dec else None
    if measure == "non_decision_share":
        return (disp - dec) / disp if disp else None
    if per_judge_count:  # dispositions per judge for an office
        return disp / per_judge_count
    return float(disp)


def _fetch_unit_rows(snapshot_id: int) -> list[dict[str, Any]]:
    """Judge×office disposition rows for one snapshot (building blocks for peer groups)."""
    return query(
        "SELECT d.office_id AS office_id, o.office_name AS office, MAX(d.region_code) AS region, "
        "a.name_key AS key, MIN(a.name_raw) AS judge, "
        f"{SUM_COLUMNS} FROM alj_disposition d JOIN alj a ON a.alj_id = d.alj_id "
        "JOIN hearing_office o ON o.office_id = d.office_id "
        "WHERE d.snapshot_id = ? GROUP BY d.office_id, a.name_key",
        (snapshot_id,),
    )


def _round(v: float | None, digits: int = 4) -> float | None:
    return None if v is None else round(v, digits)


@handled
def outlier_report(
    level: str = "office",
    measure: str = "allowance_rate",
    fiscal_year: int | None = None,
    region: str | None = None,
    min_decisions: int | None = None,
    min_z: float = 2.0,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """Flag offices or judges whose measure is |z| >= min_z vs the national peer group.

    Inputs: level, measure, FY, optional region, thresholds, pagination.
    Output: paginated outliers with peer_group stats and case-mix caveats.
    """
    if level not in ("office", "judge"):
        return error("level must be 'office' or 'judge'.")
    if measure not in MEASURES:
        return error(f"Unknown measure '{measure}'.", f"Use one of: {list(MEASURES)}")
    snap, err = resolve_snapshot(fiscal_year, None)
    if err:
        return err
    min_dec = min_decisions if min_decisions is not None else (1000 if level == "office" else 200)
    region = normalize_region(region)
    rows = _fetch_unit_rows(snap["snapshot_id"])

    office_tot: dict[int, dict[str, Any]] = {}
    region_tot: dict[str, dict[str, Any]] = {}
    national = zero_sums()
    judge_tot: dict[str, dict[str, Any]] = {}
    for r in rows:
        o = office_tot.setdefault(
            r["office_id"],
            {"office": r["office"], "region": r["region"], "judges": set(), **zero_sums()},
        )
        o["judges"].add(r["key"])
        add_sums(o, r)
        if r["region"]:
            add_sums(region_tot.setdefault(r["region"], zero_sums()), r)
        add_sums(national, r)
        j = judge_tot.setdefault(r["key"], {"judge": r["judge"], "offices": {}, **zero_sums()})
        add_sums(j, r)
        j["offices"][r["office_id"]] = r

    national_value = _raw_value(measure, national, None) if measure != "dispositions" else None

    units: list[dict[str, Any]] = []
    if level == "office":
        for oid, o in office_tot.items():
            if o["total_decisions"] < min_dec:
                continue
            n_judges = len(o["judges"])
            v = _raw_value(measure, o, n_judges)
            if v is None:
                continue
            units.append(
                {
                    "unit": o["office"],
                    "region": o["region"],
                    "judges": n_judges,
                    "total_decisions": o["total_decisions"],
                    "total_dispositions": o["total_dispositions"],
                    "_v": v,
                    "_ctx": {
                        "region_value": _round(
                            _raw_value(measure, region_tot[o["region"]], None)
                            if measure != "dispositions" and o["region"] in region_tot
                            else None
                        )
                    },
                }
            )
    else:
        for k, j in judge_tot.items():
            if j["total_decisions"] < min_dec:
                continue
            v = _raw_value(measure, j, None)
            if v is None:
                continue
            primary = max(j["offices"].values(), key=lambda r: r["total_dispositions"])
            office = office_tot[primary["office_id"]]
            ctx: dict[str, Any] = {}
            if measure != "dispositions":
                rest = {f: office[f] - primary[f] for f in SUM_FIELDS}
                rest_v = _raw_value(measure, rest, None) if rest["total_decisions"] > 0 else None
                ctx["office_value_excluding_judge"] = _round(rest_v)
                ctx["gap_vs_office_pts"] = (
                    round((v - rest_v) * 100, 1) if rest_v is not None else None
                )
            units.append(
                {
                    "unit": j["judge"],
                    "primary_office": primary["office"],
                    "region": primary["region"],
                    "offices": sorted({r["office"] for r in j["offices"].values()}),
                    "total_decisions": j["total_decisions"],
                    "total_dispositions": j["total_dispositions"],
                    "_v": v,
                    "_ctx": ctx,
                }
            )

    if len(units) < 5:
        return error(
            f"Only {len(units)} {level}s meet min_decisions={min_dec}; too few to find outliers.",
            "Lower min_decisions or choose another fiscal year.",
        )
    values = [u["_v"] for u in units]
    mean, sd = statistics.fmean(values), statistics.pstdev(values)
    items = []
    for u in units:
        if region and u.get("region") != region:
            continue
        z = (u["_v"] - mean) / sd if sd else 0.0
        if abs(z) < min_z:
            continue
        item = {k: v for k, v in u.items() if not k.startswith("_")}
        item["value"] = _round(u["_v"], 1 if measure == "dispositions" else 4)
        item["z_score"] = round(z, 2)
        item["direction"] = "high" if z > 0 else "low"
        item.update(u["_ctx"])
        items.append(item)
    items.sort(key=lambda i: -abs(i["z_score"]))
    result = paginate(items, limit, offset)
    result.update(
        {
            "level": level,
            "measure": measure,
            "snapshot": snapshot_ref(snap),
            "peer_group": {
                "units": len(units),
                "min_decisions": min_dec,
                "mean": _round(mean, 1 if measure == "dispositions" else 4),
                "stdev": _round(sd, 1 if measure == "dispositions" else 4),
                "national_value": _round(national_value),
                "scope": "all offices nationally" if level == "office" else "all judges nationally",
            },
            "min_z": min_z,
            "notes": [
                CASE_MIX_NOTE,
                CUMULATIVE_NOTE,
                "z_score = (value - peer mean) / peer standard deviation. "
                + (
                    "'dispositions' means dispositions per judge for offices and total dispositions for judges."
                    if measure == "dispositions"
                    else ""
                ),
            ],
        }
    )
    return result


@handled
def within_office_variation(
    office: str | None = None,
    region: str | None = None,
    fiscal_year: int | None = None,
    min_decisions: int = 100,
    min_judges: int = 5,
    sort_by: str = "gap",
    limit: int = 15,
    offset: int = 0,
) -> dict[str, Any]:
    """Rank hearing offices by spread of judge allowance rates within the office.

    Inputs: optional office/region/FY filters, min decisions per judge, sort, pagination.
    Output: paginated office rows with gap/stdev/median and case-mix caveats.
    """
    if sort_by not in ("gap", "stdev", "judges"):
        return error("sort_by must be 'gap', 'stdev' or 'judges'.")
    snap, err = resolve_snapshot(fiscal_year, None)
    if err:
        return err
    clauses, params = ["d.snapshot_id = ?"], [snap["snapshot_id"]]
    if office:
        office_ids = office_ids_matching(office)
        if not office_ids:
            return error(
                f"No hearing office matches '{office}'.",
                "Use ssa_alj_compare_offices to list offices.",
            )
        clauses.append(f"d.office_id IN ({','.join('?' for _ in office_ids)})")
        params += office_ids
    region = normalize_region(region)
    if region:
        clauses.append("d.region_code = ?")
        params.append(region)
    rows = query(
        "SELECT d.office_id AS office_id, o.office_name AS office, MAX(d.region_code) AS region, "
        "MIN(a.name_raw) AS judge, "
        f"{SUM_COLUMNS} FROM alj_disposition d JOIN alj a ON a.alj_id = d.alj_id "
        "JOIN hearing_office o ON o.office_id = d.office_id "
        f"WHERE {' AND '.join(clauses)} GROUP BY d.office_id, a.name_key",
        params,
    )
    by_office: dict[int, dict[str, Any]] = {}
    for r in rows:
        g = by_office.setdefault(
            r["office_id"],
            {"office": r["office"], "region": r["region"], "judges": [], "all": zero_sums()},
        )
        add_sums(g["all"], r)
        if r["total_decisions"] >= min_decisions:
            g["judges"].append(
                {
                    "judge": r["judge"],
                    "total_decisions": r["total_decisions"],
                    "total_dispositions": r["total_dispositions"],
                    "allowance_rate": rate(r["total_awards"], r["total_decisions"]),
                }
            )
    needed = 2 if office else min_judges
    items = []
    for g in by_office.values():
        js = [j for j in g["judges"] if j["allowance_rate"] is not None]
        if len(js) < needed:
            continue
        rates = [j["allowance_rate"] for j in js]
        ordered = sorted(js, key=lambda j: j["allowance_rate"])
        item: dict[str, Any] = {
            "office": g["office"],
            "region": g["region"],
            "judges_compared": len(js),
            "office_allowance_rate": rate(g["all"]["total_awards"], g["all"]["total_decisions"]),
            "lowest": ordered[0],
            "highest": ordered[-1],
            "gap_pts": round((max(rates) - min(rates)) * 100, 1),
            "median": round(statistics.median(rates), 4),
            "stdev_pts": round(statistics.pstdev(rates) * 100, 1),
        }
        if office:
            item["judges"] = ordered[::-1][:60]
        items.append(item)
    key = {"gap": "gap_pts", "stdev": "stdev_pts", "judges": "judges_compared"}[sort_by]
    items.sort(key=lambda i: (-i[key], i["office"]))
    result = paginate(items, limit, offset)
    result.update(
        {
            "snapshot": snapshot_ref(snap),
            "filters": {
                "office": office,
                "region": region,
                "min_decisions_per_judge": min_decisions,
                "min_judges": needed,
                "sort_by": sort_by,
            },
            "notes": [
                CASE_MIX_NOTE,
                CUMULATIVE_NOTE,
                "gap_pts = highest minus lowest judge allowance rate within the office (percentage points). "
                "Judges with fewer than min_decisions_per_judge decisions are excluded from the comparison "
                "(e.g. part-year or new judges).",
            ],
        }
    )
    return result
