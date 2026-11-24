"""ssa_alj_compare_offices — rank hearing offices."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ssa_alj_mcp.models import (
    FiscalYear,
    OfficeSortKey,
    PaginationParams,
    PeriodEnd,
    RegionCode,
    ResponseFormat,
)
from ssa_alj_mcp.services import offices
from ssa_alj_mcp.tools._common import (
    LOOKUP,
    ResponseFormatParam,
    annotations,
    page_args,
    shaped,
    tool_group,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="ssa_alj_compare_offices",
        **tool_group(LOOKUP),
        annotations=annotations("Rank hearing offices by disposition rates or volume"),
    )
    async def ssa_alj_compare_offices(
        fiscal_year: FiscalYear | None = None,
        as_of: PeriodEnd | None = None,
        region: RegionCode | None = None,
        min_decisions: Annotated[
            int,
            Field(
                description=(
                    "Hide offices with fewer total_decisions than this. Example: 1000. Default 0."
                ),
                ge=0,
            ),
        ] = 0,
        sort_by: Annotated[
            OfficeSortKey,
            Field(
                description=(
                    "Measure to rank by: allowance_rate | denial_rate | total_decisions | "
                    "total_dispositions | judges | dispositions_per_judge. Default allowance_rate."
                )
            ),
        ] = "allowance_rate",
        descending: Annotated[
            bool, Field(description="True = high-to-low (default); False = low-to-high.")
        ] = True,
        pagination: PaginationParams | None = None,
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """Rank hearing offices by allowance rate, denials, volume, etc. for one snapshot.

        For SSA's dispositions-per-day National Ranking use ssa_alj_office_processing_ranking
        instead. If both as_of and fiscal_year are set, as_of wins; omit both for the latest
        FY-final snapshot.
        """
        limit, offset = page_args(pagination)
        payload = await asyncio.to_thread(
            offices.compare_offices,
            fiscal_year,
            as_of,
            region,
            min_decisions,
            sort_by,
            descending,
            limit,
            offset,
        )
        return shaped(payload, response_format, title="Hearing office comparison")
