"""Judge movement between hearing offices and headcount change between fiscal years."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ssa_alj_mcp.db import query
from ssa_alj_mcp.office_aliases import canonical_office
from ssa_alj_mcp.services.common import available_fiscal_years, handled
from ssa_alj_mcp.services.offices import office_base
from ssa_alj_mcp.utils import error, normalize_key, paginate


def _judges_by_office(fy: int) -> dict[str, dict[str, Any]]:
    rows = query(
        "SELECT a.name_key AS k, MIN(a.name_raw) AS name, o.office_name AS office "
        "FROM alj_disposition d JOIN alj a ON a.alj_id = d.alj_id "
        "JOIN hearing_office o ON o.office_id = d.office_id "
        "JOIN v_fy_final_snapshot s ON s.snapshot_id = d.snapshot_id "
        "WHERE s.fiscal_year = ? GROUP BY a.name_key, o.office_name",
        (fy,),
    )
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        j = out.setdefault(r["k"], {"name": r["name"], "offices": set()})
        j["offices"].add(canonical_office(office_base(r["office"])))
    return out


@handled
def judge_movements(
    from_fiscal_year: int,
    to_fiscal_year: int,
    office: str | None = None,
    include_judges: bool = True,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """Compare judge office assignments between two fiscal-year final snapshots.

    Inputs: from/to FY, optional office filter, whether to list movers, pagination.
    Output: summary counts, per-office table, optional moved_judges page, notes.
    """
    years = available_fiscal_years()
    for fy in (from_fiscal_year, to_fiscal_year):
        if fy not in years:
            return error(f"No data for fiscal year {fy}.", f"Available fiscal years: {years}")
    a, b = _judges_by_office(from_fiscal_year), _judges_by_office(to_fiscal_year)

    status: dict[str, str] = {}
    for k in set(a) | set(b):
        if k in a and k in b:
            status[k] = "stayed" if a[k]["offices"] & b[k]["offices"] else "moved"
        else:
            status[k] = "left_data" if k in a else "new_in_data"

    tokens = set(normalize_key(office).split()) if office else set()

    def office_match(base: str) -> bool:
        return not tokens or tokens <= set(normalize_key(base).split())

    bases = {x for j in a.values() for x in j["offices"]} | {
        x for j in b.values() for x in j["offices"]
    }
    table = []
    for base in bases:
        if not office_match(base):
            continue
        row = {
            "office": base,
            "judges_from": 0,
            "judges_to": 0,
            "moved_in": 0,
            "moved_out": 0,
            "new_in_data": 0,
            "left_data": 0,
        }
        for k, st in status.items():
            in_a = k in a and base in a[k]["offices"]
            in_b = k in b and base in b[k]["offices"]
            row["judges_from"] += in_a
            row["judges_to"] += in_b
            if st == "moved":
                row["moved_in"] += in_b
                row["moved_out"] += in_a
            elif st == "new_in_data":
                row["new_in_data"] += in_b
            elif st == "left_data":
                row["left_data"] += in_a
        row["net_change"] = row["judges_to"] - row["judges_from"]
        if row["judges_to"] == 0:
            row["flag"] = (
                "no judges in the later year after alias merge - may be closed or an unmapped rename"
            )
        elif row["judges_from"] == 0:
            row["flag"] = (
                "no judges in the earlier year after alias merge - may be new or an unmapped rename"
            )
        table.append(row)
    table.sort(key=lambda r: (-abs(r["net_change"]), r["office"]))

    counts = {
        s: sum(1 for v in status.values() if v == s)
        for s in ("stayed", "moved", "left_data", "new_in_data")
    }
    result: dict[str, Any] = {
        "from_fiscal_year": from_fiscal_year,
        "to_fiscal_year": to_fiscal_year,
        "summary": {
            "judges_from": len(a),
            "judges_to": len(b),
            "net_change": len(b) - len(a),
            **counts,
        },
        "offices": paginate(table, limit, offset),
    }
    if include_judges:
        movers = []
        for k, st in status.items():
            if st != "moved":
                continue
            if tokens and not (
                _office_match_any(a[k]["offices"], office_match)
                or _office_match_any(b[k]["offices"], office_match)
            ):
                continue
            movers.append(
                {
                    "judge": b[k]["name"],
                    "from_offices": sorted(a[k]["offices"]),
                    "to_offices": sorted(b[k]["offices"]),
                }
            )
        movers.sort(key=lambda m: m["judge"])
        result["moved_judges"] = paginate(movers, limit, 0)
    result["notes"] = [
        "Known renames (Houston-Bissonnet→Houston West, Phoenix→Phoenix Downtown, West Des Moines→Des Moines) are merged via office_aliases before counting moves.",
        "Offices flagged as having no judges in one of the years are often renames or splits "
        "(compare them with the moved judges' destinations) rather than real closures.",
        "Compares the final snapshots of the two fiscal years. 'new_in_data' / 'left_data' means a "
        "published name appears or disappears; it may be a hire, retirement, reassignment to an "
        "unpublished role or a name change - the data does not say which.",
        "Offices are merged by city name; a genuine renaming or split (e.g. 'ATLANTA, GA' to 'ATLANTA "
        "NORTH') can appear as moves. Judges are matched by published name only.",
    ]
    return result


def _office_match_any(offices: set[str], fn: Callable[[str], bool]) -> bool:
    """True if any office name in `offices` satisfies predicate `fn`."""
    return any(fn(o) for o in offices)
