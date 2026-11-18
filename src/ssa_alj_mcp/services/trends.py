"""Time-based views: national/regional trend, monthly pace, period comparison."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from ssa_alj_mcp.db import query
from ssa_alj_mcp.services.common import (
    CUMULATIVE_NOTE,
    RATE_NOTE,
    add_sums,
    available_fiscal_years,
    enrich,
    handled,
    in_clause,
    non_decision_share,
    normalize_region,
    pct_change,
    pts,
    resolve_snapshot,
    zero_sums,
)
from ssa_alj_mcp.services.offices import office_base, office_ids_matching
from ssa_alj_mcp.services.sql import JOIN_FY_FINAL, SUM_COLUMNS
from ssa_alj_mcp.utils import error, normalize_key, paginate, rate


@handled
def national_trend(
    group_by: str = "national",
    region: str | None = None,
    from_fiscal_year: int | None = None,
    to_fiscal_year: int | None = None,
) -> dict[str, Any]:
    """Return a FY series of national or regional disposition totals and rates.

    Inputs: `group_by` (`national`|`region`), optional region filter and FY range.
    Output: `{group_by, region, series, highlights?, notes}` or an error payload.
    """
    if group_by not in ("national", "region"):
        return error("group_by must be 'national' or 'region'.")
    clauses, params = ["1=1"], []
    region = normalize_region(region)
    if region:
        clauses.append("d.region_code = ?")
        params.append(region)
    if group_by == "region":
        clauses.append("d.region_code IS NOT NULL")
    if from_fiscal_year is not None:
        clauses.append("s.fiscal_year >= ?")
        params.append(from_fiscal_year)
    if to_fiscal_year is not None:
        clauses.append("s.fiscal_year <= ?")
        params.append(to_fiscal_year)
    region_sel = "d.region_code AS region," if group_by == "region" else ""
    group = "s.fiscal_year, d.region_code" if group_by == "region" else "s.fiscal_year"
    rows = query(
        f"SELECT s.fiscal_year AS fiscal_year, s.reporting_period_end AS as_of, {region_sel} "
        "COUNT(DISTINCT a.name_key) AS judges, COUNT(DISTINCT d.office_id) AS offices, "
        f"{SUM_COLUMNS} FROM alj_disposition d JOIN alj a ON a.alj_id = d.alj_id "
        "JOIN v_fy_final_snapshot s ON s.snapshot_id = d.snapshot_id "
        f"WHERE {' AND '.join(clauses)} GROUP BY {group}, s.reporting_period_end "
        "ORDER BY " + ("region, " if group_by == "region" else "") + "s.fiscal_year",
        params,
    )
    if not rows:
        return error(
            "No data for those filters.", f"Available fiscal years: {available_fiscal_years()}"
        )
    series: list[dict[str, Any]] = []
    prev: dict[Any, dict[str, Any]] = {}
    for r in rows:
        e = enrich(r)
        e["non_decision_share"] = non_decision_share(r)
        e["dispositions_per_judge"] = (
            round(r["total_dispositions"] / r["judges"], 1) if r["judges"] else None
        )
        p = prev.get(r.get("region"))
        e["allowance_rate_change_pts"] = (
            pts(e["allowance_rate"], p["allowance_rate"]) if p else None
        )
        e["dispositions_change_pct"] = (
            pct_change(r["total_dispositions"], p["total_dispositions"]) if p else None
        )
        e["judges_change"] = r["judges"] - p["judges"] if p else None
        prev[r.get("region")] = e
        series.append(e)
    result: dict[str, Any] = {"group_by": group_by, "region": region, "series": series}
    if group_by == "national" or region:
        valid = [s for s in series if s["allowance_rate"] is not None]
        result["highlights"] = {
            "highest_allowance_rate": _pick(valid, "allowance_rate", max),
            "lowest_allowance_rate": _pick(valid, "allowance_rate", min),
            "peak_dispositions": _pick(series, "total_dispositions", max),
            "lowest_dispositions": _pick(series, "total_dispositions", min),
            "peak_judges": _pick(series, "judges", max),
            "fewest_judges": _pick(series, "judges", min),
        }
    result["notes"] = [
        CUMULATIVE_NOTE,
        RATE_NOTE,
        "judges = distinct published judge names with a row in the fiscal year's final snapshot. "
        "non_decision_share = other_dispositions / total_dispositions. The most recent fiscal year "
        "may be a current, not-yet-final report.",
    ]
    return result


def _pick(
    rows: list[dict[str, Any]],
    field: str,
    fn: Callable[..., dict[str, Any]],
) -> dict[str, Any] | None:
    """Return `{fiscal_year, region?, field}` for the row selected by `fn` (e.g. min/max)."""
    if not rows:
        return None
    best = fn(rows, key=lambda r: r[field])
    return {"fiscal_year": best["fiscal_year"], "region": best.get("region"), field: best[field]}


@handled
def monthly_pace(
    fiscal_year: int | None = None, office: str | None = None, region: str | None = None
) -> dict[str, Any]:
    """Difference consecutive FYTD snapshots into per-period pace metrics.

    Inputs: optional fiscal year, office name filter, region code.
    Output: `{fiscal_year, filters, periods, notes, ...}` or an error payload.
    """
    snap, err = resolve_snapshot(fiscal_year, None)
    if err:
        return err
    fy = snap["fiscal_year"]
    clauses, params = ["s.report_kind = 'alj_disposition'", "s.fiscal_year = ?"], [fy]
    matched_offices: list[str] | None = None
    if office:
        ids = office_ids_matching(office)
        if not ids:
            return error(
                f"No hearing office matches '{office}'.",
                "Use ssa_alj_compare_offices to list offices.",
            )
        names = query(
            f"SELECT office_name FROM hearing_office WHERE office_id IN ({in_clause(ids)})", ids
        )
        matched_offices = sorted(n["office_name"] for n in names)
        clauses.append(f"d.office_id IN ({in_clause(ids)})")
        params += ids
    region = normalize_region(region)
    if region:
        clauses.append("d.region_code = ?")
        params.append(region)
    rows = query(
        "SELECT s.reporting_period_end AS period_end, s.report_label AS report, "
        f"{SUM_COLUMNS} FROM report_snapshot s JOIN alj_disposition d ON d.snapshot_id = s.snapshot_id "
        f"WHERE {' AND '.join(clauses)} GROUP BY s.snapshot_id ORDER BY s.reporting_period_end, s.snapshot_id",
        params,
    )
    if not rows:
        return error(f"No data for fiscal year {fy} with those filters.")
    fy_start = date(fy - 1, 10, 1)
    out: list[dict[str, Any]] = []
    prev = None
    for r in rows:
        end = date.fromisoformat(r["period_end"])
        start = fy_start if prev is None else date.fromisoformat(prev["period_end"])
        days = (end - start).days + (1 if prev is None else 0)
        d_disp = r["total_dispositions"] - (prev["total_dispositions"] if prev else 0)
        d_dec = r["total_decisions"] - (prev["total_decisions"] if prev else 0)
        d_aw = r["total_awards"] - (prev["total_awards"] if prev else 0)
        item: dict[str, Any] = {
            "period_end": r["period_end"],
            "report": r["report"],
            "days_covered": days,
            "dispositions_in_period": d_disp,
            "decisions_in_period": d_dec,
            "allowance_rate_in_period": rate(d_aw, d_dec),
            "dispositions_per_day": round(d_disp / days, 1) if days > 0 else None,
            "fytd_dispositions": r["total_dispositions"],
            "fytd_allowance_rate": rate(r["total_awards"], r["total_decisions"]),
        }
        flags = []
        if days > 45:
            flags.append(
                f"covers {days} days - one or more monthly snapshots are missing or this is the first/only snapshot"
            )
        if d_disp < 0:
            flags.append(
                "negative change: judges or rows moved out of this filter, or SSA revised counts"
            )
        if flags:
            item["flags"] = flags
        out.append(item)
        prev = r
    result: dict[str, Any] = {
        "fiscal_year": fy,
        "filters": {"office": office, "region": region},
        "offices_matched": matched_offices,
        "snapshots": len(out),
        "periods": out,
        "notes": [
            "Each period is the difference between consecutive cumulative snapshots, so it is the "
            "output for that period only. Compare dispositions_per_day, not raw totals, when "
            "periods have different lengths.",
            "If an office filter is used, judges who change offices during the year can make "
            "period figures look low or negative.",
        ],
    }
    if len(out) >= 3 and all(o["dispositions_per_day"] for o in out[-2:]):
        result["latest_vs_previous_pct"] = pct_change(
            out[-1]["dispositions_per_day"], out[-2]["dispositions_per_day"]
        )
    return result


_ENTITIES = ("office", "region", "judge")
_COMPARE_SORTS = ("allowance_rate_change", "dispositions_change_pct", "decisions_change_pct")


def _entity_sums(entity: str, fy: int) -> dict[str, dict[str, Any]]:
    """Aggregate disposition sums keyed by office base / region / judge name_key for one FY."""
    base = JOIN_FY_FINAL
    out: dict[str, dict[str, Any]] = {}
    if entity == "office":
        rows = query(
            f"SELECT o.office_name AS label, COUNT(DISTINCT a.name_key) AS judges, {SUM_COLUMNS} {base}"
            "JOIN hearing_office o ON o.office_id = d.office_id WHERE s.fiscal_year = ? GROUP BY d.office_id",
            (fy,),
        )
        keyf = office_base
    elif entity == "region":
        rows = query(
            f"SELECT d.region_code AS label, COUNT(DISTINCT a.name_key) AS judges, {SUM_COLUMNS} {base}"
            "WHERE s.fiscal_year = ? AND d.region_code IS NOT NULL GROUP BY d.region_code",
            (fy,),
        )
        keyf = str
    else:
        rows = query(
            f"SELECT a.name_key AS key, MIN(a.name_raw) AS label, 1 AS judges, {SUM_COLUMNS} {base}"
            "WHERE s.fiscal_year = ? GROUP BY a.name_key",
            (fy,),
        )
        keyf = None
    for r in rows:
        key = r["key"] if entity == "judge" else keyf(r["label"])
        if key not in out:
            out[key] = {
                "label": key if entity != "judge" else r["label"],
                "judges": 0,
                **zero_sums(),
            }
        out[key]["judges"] += r["judges"]
        add_sums(out[key], r)
    return out


def _measures(s: dict[str, Any], entity: str) -> dict[str, Any]:
    """Derived rates/shares for one entity's summed row."""
    e = enrich({k: s[k] for k in s if k not in ("label", "judges")})
    e["non_decision_share"] = non_decision_share(s)
    if entity != "judge":
        e["judges"] = s["judges"]
        e["dispositions_per_judge"] = (
            round(s["total_dispositions"] / s["judges"], 1) if s["judges"] else None
        )
    return e


def _change(a: dict[str, Any] | None, b: dict[str, Any] | None) -> dict[str, Any]:
    """Delta metrics between two enriched measure dicts."""
    if not a or not b:
        return {}
    return {
        "allowance_rate_change_pts": pts(b["allowance_rate"], a["allowance_rate"]),
        "dispositions_change": b["total_dispositions"] - a["total_dispositions"],
        "dispositions_change_pct": pct_change(b["total_dispositions"], a["total_dispositions"]),
        "decisions_change_pct": pct_change(b["total_decisions"], a["total_decisions"]),
    }


def _case_mix_note() -> str:
    return (
        "Rates are not adjusted for case mix, claimant mix or office workload; a change is "
        "descriptive, not evidence of why it happened."
    )


@handled
def compare_periods(
    entity: str,
    fiscal_year_a: int,
    fiscal_year_b: int,
    name: str | None = None,
    min_decisions: int = 500,
    sort_by: str = "allowance_rate_change",
    direction: str = "largest_move",
    limit: int = 15,
    offset: int = 0,
) -> dict[str, Any]:
    """Compare offices, regions, or judges between two fiscal years.

    Inputs: entity type, two FYs, optional name filter, min decisions, sort, pagination.
    Output: single-entity detail or a paginated movers list, plus notes.
    """
    if entity not in _ENTITIES:
        return error(f"entity must be one of {list(_ENTITIES)}.")
    if sort_by not in _COMPARE_SORTS or direction not in ("largest_move", "increase", "decrease"):
        return error("Invalid sort_by or direction.", f"sort_by: {list(_COMPARE_SORTS)}")
    years = available_fiscal_years()
    for fy in (fiscal_year_a, fiscal_year_b):
        if fy not in years:
            return error(f"No data for fiscal year {fy}.", f"Available fiscal years: {years}")
    a_all, b_all = _entity_sums(entity, fiscal_year_a), _entity_sums(entity, fiscal_year_b)
    keys = set(a_all) | set(b_all)

    if name:
        wanted = normalize_region(name) if entity == "region" else normalize_key(name)
        if entity == "region":
            keys = {k for k in keys if k == wanted}
        else:
            tokens = set(wanted.split())
            keys = {k for k in keys if tokens <= set(normalize_key(k).split())}
        if not keys:
            return error(f"No {entity} matches '{name}'.", "Check the spelling or search first.")
        exact = [k for k in keys if normalize_key(k) == normalize_key(name)]
        if len(keys) > 1 and len(exact) == 1:
            keys = set(exact)
        if len(keys) > 1:
            labels = sorted((a_all.get(k) or b_all[k])["label"] for k in keys)
            return error(
                f"'{name}' matches {len(keys)} {entity}s; be more specific.", candidates=labels[:15]
            )
        k = next(iter(keys))
        a, b = a_all.get(k), b_all.get(k)
        ma, mb = (_measures(a, entity) if a else None), (_measures(b, entity) if b else None)
        return {
            "entity": entity,
            "name": (a or b)["label"],
            f"fy{fiscal_year_a}": ma,
            f"fy{fiscal_year_b}": mb,
            "change": _change(ma, mb),
            "notes": [CUMULATIVE_NOTE, RATE_NOTE, _case_mix_note()],
        }

    items = []
    only_a = only_b = below_min = 0
    for k in keys:
        a, b = a_all.get(k), b_all.get(k)
        if not a:
            only_b += 1
            continue
        if not b:
            only_a += 1
            continue
        if a["total_decisions"] < min_decisions or b["total_decisions"] < min_decisions:
            below_min += 1
            continue
        ma, mb = _measures(a, entity), _measures(b, entity)
        ch = _change(ma, mb)
        metric = {"allowance_rate_change": "allowance_rate_change_pts"}.get(sort_by, sort_by)
        if ch.get(metric) is None:
            continue
        items.append(
            {
                "name": b["label"],
                f"fy{fiscal_year_a}": {
                    "judges": ma.get("judges"),
                    "total_decisions": ma["total_decisions"],
                    "total_dispositions": ma["total_dispositions"],
                    "allowance_rate": ma["allowance_rate"],
                },
                f"fy{fiscal_year_b}": {
                    "judges": mb.get("judges"),
                    "total_decisions": mb["total_decisions"],
                    "total_dispositions": mb["total_dispositions"],
                    "allowance_rate": mb["allowance_rate"],
                },
                "change": ch,
                "_sort": ch[metric],
            }
        )
    if direction == "largest_move":
        items.sort(key=lambda i: -abs(i["_sort"]))
    elif direction == "increase":
        items.sort(key=lambda i: -i["_sort"])
    else:
        items.sort(key=lambda i: i["_sort"])
    for i in items:
        del i["_sort"]
    result = paginate(items, limit, offset)
    result.update(
        {
            "entity": entity,
            "compared": [fiscal_year_a, fiscal_year_b],
            "sort_by": sort_by,
            "direction": direction,
            "excluded": {
                "present_only_in_first_year": only_a,
                "present_only_in_second_year": only_b,
                f"below_{min_decisions}_decisions_in_either_year": below_min,
            },
            "notes": [CUMULATIVE_NOTE, RATE_NOTE, _case_mix_note()],
        }
    )
    return result
