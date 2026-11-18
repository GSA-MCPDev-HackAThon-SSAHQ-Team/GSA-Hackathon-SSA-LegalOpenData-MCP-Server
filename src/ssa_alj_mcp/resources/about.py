"""ssa-alj://about - data dictionary and reading guide."""

from __future__ import annotations

from fastmcp import FastMCP

ABOUT = """\
# SSA ALJ Disposition Data - reading guide

Source: SSA Office of Hearings Operations (OHO), Social Security hearings. Published as XML at
https://www.ssa.gov/appeals/DataSets/ and catalogued on Data.gov (collection US-GOV-SSA-1199).
Public data. Judges are identified by published name only.

## Measures (per judge x hearing office x snapshot)
- fully_favorable, partially_favorable: decisions that grant benefits (total_awards = sum).
- total_denials: decisions that deny benefits.
- total_decisions = awards + denials.
- total_dispositions >= total_decisions; the difference (other_dispositions) is non-decision
  outcomes such as dismissals (inferred, not documented by SSA).
- allowance_rate = total_awards / total_decisions; denial_rate = total_denials / total_decisions.

## Time
- Counts are cumulative from Oct 1 of the federal fiscal year to the snapshot's period end, and reset
  each October. The September snapshot is the full fiscal year. Never add snapshots together.
- Coverage: fiscal years 2010-2026 (FY2026 may be a "current report" snapshot).

## Caveats
- No judge ID: namesakes are indistinguishable. Judges who change office appear under each office.
- Office names change over time and are merged by city name on a best-effort basis.
- Rates reflect case mix and are not a measure of judge quality or correctness.

## Tools

Core (lookup): ssa_alj_list_reports, ssa_alj_search_judges, ssa_alj_get_judge_profile,
ssa_alj_compare_offices, ssa_alj_get_office_profile, ssa_alj_office_processing_ranking.

Analysis: ssa_alj_national_trend, ssa_alj_monthly_pace, ssa_alj_compare_periods,
ssa_alj_outlier_report, ssa_alj_within_office_variation, ssa_alj_judge_movements,
ssa_alj_data_quality_notes.

Response contract: list tools return {total,count,offset,has_more,next_offset,items,notes}.
Snapshot tools include snapshot:{period_end,fiscal_year,report}. Optional response_format=markdown.

"""


def register(mcp: FastMCP) -> None:
    @mcp.resource("ssa-alj://about", mime_type="text/markdown")
    def about() -> str:
        """Data dictionary and caveats for the SSA ALJ disposition data."""
        return ABOUT
