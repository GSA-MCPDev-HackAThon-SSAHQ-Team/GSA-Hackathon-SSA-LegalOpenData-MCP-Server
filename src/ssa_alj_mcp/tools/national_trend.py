"""ssa_alj_national_trend — multi-year national / regional series."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ssa_alj_mcp.models import FiscalYear, RegionCode, ResponseFormat, TrendGroupBy
from ssa_alj_mcp.services import trends
from ssa_alj_mcp.tools._common import ResponseFormatParam, annotations, shaped


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="ssa_alj_national_trend",
        annotations=annotations("Multi-year national or regional disposition series"),
    )
    async def ssa_alj_national_trend(
        group_by: Annotated[
            TrendGroupBy,
            Field(
                description=(
                    "'national' = one series for all offices; 'region' = one series per region. "
                    "Default national."
                )
            ),
        ] = "national",
        region: RegionCode | None = None,
        from_fiscal_year: FiscalYear | None = None,
        to_fiscal_year: FiscalYear | None = None,
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """National or regional disposition series across fiscal years (FY-final snapshots).

        For within-year speed-up/slow-down use ssa_alj_monthly_pace; for biggest movers between
        two specific years use ssa_alj_compare_periods.
        """
        payload = await asyncio.to_thread(
            trends.national_trend, group_by, region, from_fiscal_year, to_fiscal_year
        )
        return shaped(payload, response_format, title="National / regional trend")
