"""Which SSA reports (snapshots) are in the database."""

from __future__ import annotations

from typing import Any

from ssa_alj_mcp.db import query
from ssa_alj_mcp.services.common import CUMULATIVE_NOTE, handled


@handled
def list_reports(fiscal_year: int | None = None) -> dict[str, Any]:
    """Return dataset coverage and available disposition/ranking snapshots.

    Inputs: optional fiscal_year to list mid-year snapshots for that FY.
    Output: coverage metadata, FY-final list, ranking list, notes.
    """
    final = query(
        "SELECT fiscal_year, reporting_period_end AS period_end, report_label AS report, "
        "loaded_row_count AS rows FROM v_fy_final_snapshot ORDER BY fiscal_year"
    )
    ranking = query(
        "SELECT fiscal_year, reporting_period_end AS period_end, report_label AS report, "
        "loaded_row_count AS offices FROM report_snapshot WHERE report_kind = 'office_ranking' "
        "ORDER BY reporting_period_end"
    )
    result: dict[str, Any] = {
        "dataset": "SSA Office of Hearings Operations - ALJ Disposition Data (and National Ranking Reports)",
        "source": "https://www.ssa.gov/appeals/DataSets/ (catalogued on Data.gov, collection US-GOV-SSA-1199)",
        "coverage": {
            "first_period_end": final[0]["period_end"] if final else None,
            "latest_period_end": final[-1]["period_end"] if final else None,
            "fiscal_years": [r["fiscal_year"] for r in final],
        },
        "fiscal_year_final_snapshots": final,
        "office_ranking_snapshots": ranking,
        "notes": [CUMULATIVE_NOTE],
    }
    if fiscal_year is not None:
        result["fiscal_year_snapshots"] = query(
            "SELECT reporting_period_end AS period_end, report_label AS report, "
            "loaded_row_count AS rows FROM report_snapshot "
            "WHERE report_kind = 'alj_disposition' AND fiscal_year = ? ORDER BY reporting_period_end",
            (fiscal_year,),
        )
    return result
