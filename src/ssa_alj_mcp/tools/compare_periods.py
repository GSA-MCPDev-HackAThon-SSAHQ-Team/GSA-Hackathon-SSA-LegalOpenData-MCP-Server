"""ssa_alj_compare_periods — change between two fiscal years."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ssa_alj_mcp.models import (
    EntityLevel,
    FiscalYear,
    PaginationParams,
    PeriodDirection,
    PeriodSortKey,
    ResponseFormat,
)
from ssa_alj_mcp.services import trends
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
        name="ssa_alj_compare_periods",
        **tool_group(ANALYSIS),
        annotations=annotations("Biggest movers between two fiscal years"),
    )
    async def ssa_alj_compare_periods(
        entity: Annotated[
            EntityLevel,
            Field(description="What to compare across years: office | region | judge."),
        ],
        fiscal_year_a: Annotated[
            FiscalYear, Field(description="Earlier (baseline) fiscal year, e.g. 2023.")
        ],
        fiscal_year_b: Annotated[FiscalYear, Field(description="Later fiscal year, e.g. 2024.")],
        name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional single entity name (e.g. 'CHARLESTON WV'). Omit to rank movers. "
                    "Be specific — ambiguous names return candidates."
                ),
                max_length=100,
            ),
        ] = None,
        min_decisions: Annotated[
            int,
            Field(
                description="Exclude entities below this decisions count in either year. Default 500.",
                ge=0,
            ),
        ] = 500,
        sort_by: Annotated[
            PeriodSortKey,
            Field(
                description=(
                    "Rank movers by: allowance_rate_change | dispositions_change_pct | "
                    "decisions_change_pct. Default allowance_rate_change."
                )
            ),
        ] = "allowance_rate_change",
        direction: Annotated[
            PeriodDirection,
            Field(
                description=(
                    "largest_move | increase | decrease. Default largest_move (by absolute change)."
                )
            ),
        ] = "largest_move",
        pagination: PaginationParams | None = None,
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """Side-by-side or ranked change for offices/regions/judges between two fiscal years.

        Both years are required. Omit name to list biggest movers; pass a specific name for
        one entity. For workforce joins/leaves see ssa_alj_judge_movements.
        """
        if refused := refusal_for(name):
            return shaped(refused, response_format, title="Request refused")
        # Smaller default page for mover leaderboards.
        limit, offset = page_args(pagination or PaginationParams(limit=15))
        payload = await asyncio.to_thread(
            trends.compare_periods,
            entity,
            fiscal_year_a,
            fiscal_year_b,
            name,
            min_decisions,
            sort_by,
            direction,
            limit,
            offset,
        )
        return shaped(payload, response_format, title="Period comparison")
