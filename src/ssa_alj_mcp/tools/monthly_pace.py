"""ssa_alj_monthly_pace — per-period output within a fiscal year."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ssa_alj_mcp.models import FiscalYear, RegionCode, ResponseFormat
from ssa_alj_mcp.services import trends
from ssa_alj_mcp.tools._common import (
    ANALYSIS,
    ResponseFormatParam,
    annotations,
    refusal_for,
    shaped,
    tool_group,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="ssa_alj_monthly_pace",
        **tool_group(ANALYSIS),
        annotations=annotations("Within-year pace from consecutive FYTD snapshots"),
    )
    async def ssa_alj_monthly_pace(
        fiscal_year: FiscalYear | None = None,
        office: Annotated[
            str | None,
            Field(
                description="Optional office/city filter, e.g. 'Miami'. Omit for national pace.",
                max_length=100,
            ),
        ] = None,
        region: RegionCode | None = None,
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """Within-year output pace by differencing consecutive FYTD snapshots.

        Answers whether dispositions are speeding up or slowing down inside one fiscal year —
        not a multi-year trend (see ssa_alj_national_trend).
        """
        if refused := refusal_for(office):
            return shaped(refused, response_format, title="Request refused")
        payload = await asyncio.to_thread(trends.monthly_pace, fiscal_year, office, region)
        return shaped(payload, response_format, title="Monthly pace")
