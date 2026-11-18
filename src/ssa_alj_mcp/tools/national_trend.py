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
        from_fiscal_year: Annotated[
            FiscalYear | None,
            Field(
                description=(
                    "First fiscal year of the series, e.g. 2015. "
                    "Omit for every year on record. This is not a snapshot tool: "
                    "omitting the year does not mean 'latest year only'."
                )
            ),
        ] = None,
        to_fiscal_year: Annotated[
            FiscalYear | None,
            Field(
                description=(
                    "Last fiscal year of the series, e.g. 2025. "
                    "Omit for every year on record. Passing only the latest year "
                    "returns one point, not a trend."
                )
            ),
        ] = None,
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """National or regional disposition series across fiscal years (FY-final snapshots).

        For a regional trend over time, call with group_by='region' and omit both year
        arguments. For which offices are high or low in one year, use ssa_alj_compare_offices
        (it already includes each office's region). For within-year speed-up or slow-down use
        ssa_alj_monthly_pace; for biggest movers between two specific years use
        ssa_alj_compare_periods.
        """
        payload = await asyncio.to_thread(
            trends.national_trend, group_by, region, from_fiscal_year, to_fiscal_year
        )
        return shaped(payload, response_format, title="National / regional trend")
