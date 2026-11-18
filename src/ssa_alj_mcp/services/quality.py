"""Known data gaps and caveats, computed from the database where possible."""

from __future__ import annotations

from datetime import date
from typing import Any

from ssa_alj_mcp.db import query
from ssa_alj_mcp.services.common import handled
from ssa_alj_mcp.services.offices import office_base

ISSUE_EXPLANATIONS = {
    "declared_count_mismatch": "The record count SSA declares in the file header differs from the rows in the file. Rows actually present are used.",
    "duplicate_judge_office_row": "Same judge name appears twice for one office in one report; kept (likely two judges sharing a name) and summed in judge views.",
    "decisions_ne_awards_plus_denials": "total_decisions does not equal awards + denials in the source row; values kept as published.",
    "all_offices_lt_office_dispositions": "A judge's all-offices total is smaller than the office total in the source row; kept as published.",
    "blank_office_or_region": "Row has no office or region; excluded from office/region views, counted in judge views.",
}

NOT_IN_DATASET = [
    "No case type (initial vs. appeal, SSDI vs. SSI), claimant demographics, or diagnosis.",
    "No processing time, pending/backlog counts, or wait times (only the separate National Ranking report gives dispositions per day).",
    "No judge identifier, appointment date or biographical data.",
    "No reason codes for non-decision dispositions (dismissals, withdrawals, etc.).",
    "No case-mix adjustment: allowance rates are raw published counts.",
]


@handled
def data_quality_notes() -> dict[str, Any]:
    """Summarise known gaps, load issues, and what the dataset does not contain.

    Output: coverage, snapshot_gaps, source issues, identity/office naming notes.
    """
    snaps = query(
        "SELECT fiscal_year, reporting_period_end AS p, report_label FROM report_snapshot "
        "WHERE report_kind = 'alj_disposition' ORDER BY reporting_period_end, snapshot_id"
    )
    by_fy: dict[int, list[dict[str, Any]]] = {}
    for s in snaps:
        by_fy.setdefault(s["fiscal_year"], []).append(s)
    gaps = []
    for fy, ss in sorted(by_fy.items()):
        if len(ss) == 1:
            gaps.append({"fiscal_year": fy, "issue": "only one snapshot published", "snapshots": 1})
            continue
        for prev, cur in zip(ss, ss[1:]):
            days = (date.fromisoformat(cur["p"]) - date.fromisoformat(prev["p"])).days
            if days > 45:
                gaps.append(
                    {
                        "fiscal_year": fy,
                        "issue": f"{days}-day gap between snapshots",
                        "from": prev["p"],
                        "to": cur["p"],
                    }
                )
    issues = query(
        "SELECT issue_type, COUNT(*) AS rows, COUNT(DISTINCT snapshot_id) AS reports FROM load_issue GROUP BY issue_type ORDER BY rows DESC"
    )
    for i in issues:
        i["meaning"] = ISSUE_EXPLANATIONS.get(i["issue_type"], "")
    mismatches = query(
        "SELECT reporting_period_end AS period_end, declared_record_count AS declared, loaded_row_count AS actual "
        "FROM report_snapshot WHERE declared_record_count IS NOT NULL AND declared_record_count <> loaded_row_count "
        "ORDER BY reporting_period_end"
    )
    names = query("SELECT COUNT(*) AS raw, COUNT(DISTINCT name_key) AS keys FROM alj")[0]
    offices = query("SELECT office_name FROM hearing_office")
    bases = {office_base(o["office_name"]) for o in offices}
    latest = query(
        "SELECT fiscal_year, reporting_period_end AS p, report_label FROM v_fy_final_snapshot ORDER BY fiscal_year DESC LIMIT 1"
    )[0]
    return {
        "coverage": {
            "alj_disposition_snapshots": len(snaps),
            "fiscal_years": sorted(by_fy),
            "latest_final_snapshot": {
                "fiscal_year": latest["fiscal_year"],
                "period_end": latest["p"],
                "report": latest["report_label"],
            },
        },
        "snapshot_gaps": gaps,
        "source_file_issues": issues,
        "header_count_mismatches": mismatches,
        "identity": {
            "published_name_spellings": names["raw"],
            "distinct_judges_after_folding_case_and_punctuation": names["keys"],
            "note": "No judge ID is published; namesakes cannot be told apart and name changes look like different judges.",
        },
        "office_naming": {
            "published_office_names": len(offices),
            "distinct_after_merging_variants": len(bases),
            "note": "Office names changed over the years (e.g. 'MIAMI OHO', 'MIAMI, FL'); tools merge by city name on a best-effort basis.",
        },
        "time_semantics": "Counts are cumulative from Oct 1 and reset each October; the September snapshot is the fiscal-year total. The latest fiscal year may be an in-progress or 'Current Report' snapshot.",
        "not_in_dataset": NOT_IN_DATASET,
    }
