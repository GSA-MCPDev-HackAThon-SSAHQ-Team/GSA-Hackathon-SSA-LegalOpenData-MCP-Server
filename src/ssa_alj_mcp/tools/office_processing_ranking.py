"""ssa_alj_office_processing_ranking — SSA National Ranking report."""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP

from ssa_alj_mcp.models import PaginationParams, PeriodEnd, RegionCode, ResponseFormat
from ssa_alj_mcp.services import offices
from ssa_alj_mcp.tools._common import ResponseFormatParam, annotations, page_args, shaped


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="ssa_alj_office_processing_ranking",
        annotations=annotations("SSA National Ranking by dispositions per day per ALJ"),
    )
    async def ssa_alj_office_processing_ranking(
        period_end: PeriodEnd | None = None,
        region: RegionCode | None = None,
        pagination: PaginationParams | None = None,
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """SSA National Ranking: offices by dispositions per day per ALJ (rank 1 = fastest).

        This is a separate SSA report from disposition allowance rates — do not confuse with
        ssa_alj_compare_offices. Omit period_end for the latest ranking snapshot.
        """
        limit, offset = page_args(pagination)
        payload = await asyncio.to_thread(
            offices.office_processing_ranking, period_end, region, limit, offset
        )
        return shaped(payload, response_format, title="Office processing ranking")
