"""ssa_alj_within_office_variation — judge spread inside an office."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ssa_alj_mcp.models import (
    FiscalYear,
    PaginationParams,
    RegionCode,
    ResponseFormat,
    VariationSortKey,
)
from ssa_alj_mcp.services import analysis
from ssa_alj_mcp.tools._common import (
    ANALYSIS,
    ResponseFormatParam,
    annotations,
    page_args,
    refusal_for,
    shaped,
    tool_group,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="ssa_alj_within_office_variation",
        **tool_group(ANALYSIS),
        annotations=annotations("Allowance-rate spread among judges inside an office"),
    )
    async def ssa_alj_within_office_variation(
        office: Annotated[
            str | None,
            Field(
                description=(
                    "Optional office/city, e.g. 'Miami'. Omit to rank offices by internal gap."
                ),
                max_length=100,
            ),
        ] = None,
        region: RegionCode | None = None,
        fiscal_year: FiscalYear | None = None,
        min_decisions: Annotated[
            int,
            Field(
                description="Min decisions per judge to include in the comparison. Default 100.",
                ge=1,
            ),
        ] = 100,
        min_judges: Annotated[
            int,
            Field(
                description="Min judges meeting min_decisions (ignored when office is set). Default 5.",
                ge=2,
            ),
        ] = 5,
        sort_by: Annotated[
            VariationSortKey,
            Field(description="Rank offices by: gap | stdev | judges. Default gap."),
        ] = "gap",
        pagination: PaginationParams | None = None,
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """How much judge allowance rates differ inside the same hearing office.

        Pass office for detail (e.g. Miami); omit office to rank offices by gap. Not the same as
        national peer outliers (ssa_alj_outlier_report).
        """
        if refused := refusal_for(office):
            return shaped(refused, response_format, title="Request refused")
        limit, offset = page_args(pagination or PaginationParams(limit=15))
        payload = await asyncio.to_thread(
            analysis.within_office_variation,
            office,
            region,
            fiscal_year,
            min_decisions,
            min_judges,
            sort_by,
            limit,
            offset,
        )
        return shaped(payload, response_format, title="Within-office variation")
