"""ssa_alj_outlier_report — peer outliers on published counts."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ssa_alj_mcp.models import (
    FiscalYear,
    OutlierMeasure,
    PaginationParams,
    PeerLevel,
    RegionCode,
    ResponseFormat,
)
from ssa_alj_mcp.services import analysis
from ssa_alj_mcp.tools._common import ResponseFormatParam, annotations, page_args, shaped


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="ssa_alj_outlier_report",
        annotations=annotations("Peer z-score outliers for offices or judges"),
    )
    async def ssa_alj_outlier_report(
        level: Annotated[
            PeerLevel,
            Field(description="Peer unit: 'office' (default) or 'judge'."),
        ] = "office",
        measure: Annotated[
            OutlierMeasure,
            Field(
                description=(
                    "allowance_rate | non_decision_share | dispositions "
                    "(per-judge for offices; total for judges). Default allowance_rate."
                )
            ),
        ] = "allowance_rate",
        fiscal_year: FiscalYear | None = None,
        region: RegionCode | None = None,
        min_decisions: Annotated[
            int | None,
            Field(
                description=(
                    "Minimum decisions to enter the peer group. Default 1000 (office) or 200 (judge)."
                ),
                ge=1,
            ),
        ] = None,
        min_z: Annotated[
            float,
            Field(description="Minimum |z-score| to report. Default 2.0.", ge=0, le=10),
        ] = 2.0,
        pagination: PaginationParams | None = None,
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """Offices or judges far from the national peer mean (z-score on published counts).

        Descriptive only — not case-mix adjusted. For spread inside one office use
        ssa_alj_within_office_variation; call ssa_alj_data_quality_notes before inferring cause.
        """
        limit, offset = page_args(pagination)
        payload = await asyncio.to_thread(
            analysis.outlier_report,
            level,
            measure,
            fiscal_year,
            region,
            min_decisions,
            min_z,
            limit,
            offset,
        )
        return shaped(payload, response_format, title="Outlier report")
