"""MCP tools — thin async wrappers over services (one module per tool)."""

from __future__ import annotations

from fastmcp import FastMCP

from ssa_alj_mcp.tools import (
    business_queries,
    compare_offices,
    compare_periods,
    data_quality_notes,
    get_judge_profile,
    get_office_profile,
    judge_movements,
    list_reports,
    monthly_pace,
    national_trend,
    office_processing_ranking,
    outlier_report,
    search_judges,
    source_links,
    within_office_variation,
)


def register_tools(mcp: FastMCP) -> None:
    for module in (
        list_reports,
        business_queries,
        source_links,
        search_judges,
        get_judge_profile,
        compare_offices,
        get_office_profile,
        office_processing_ranking,
        national_trend,
        monthly_pace,
        compare_periods,
        outlier_report,
        within_office_variation,
        judge_movements,
        data_quality_notes,
    ):
        module.register(mcp)
