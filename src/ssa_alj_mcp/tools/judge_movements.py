"""ssa_alj_judge_movements — headcount and office moves."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ssa_alj_mcp.models import FiscalYear, PaginationParams, ResponseFormat
from ssa_alj_mcp.services import workforce
from ssa_alj_mcp.tools._common import (
    ResponseFormatParam,
    annotations,
    page_args,
    refusal_for,
    shaped,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="ssa_alj_judge_movements",
        annotations=annotations("Judge headcount change and office-to-office moves"),
    )
    async def ssa_alj_judge_movements(
        from_fiscal_year: Annotated[
            FiscalYear, Field(description="Baseline fiscal year, e.g. 2023.")
        ],
        to_fiscal_year: Annotated[FiscalYear, Field(description="Later fiscal year, e.g. 2024.")],
        office: Annotated[
            str | None,
            Field(
                description="Optional office/city filter, e.g. 'Phoenix'.",
                max_length=100,
            ),
        ] = None,
        include_judges: Annotated[
            bool,
            Field(description="If true (default), also list judges who changed office."),
        ] = True,
        pagination: PaginationParams | None = None,
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """Judge headcount change and office moves between two FY-final snapshots.

        Both years required. This is about who appears where — not rate changes
        (ssa_alj_compare_periods) or a single judge's disposition history.
        """
        if refused := refusal_for(office):
            return shaped(refused, response_format, title="Request refused")
        limit, offset = page_args(pagination)
        payload = await asyncio.to_thread(
            workforce.judge_movements,
            from_fiscal_year,
            to_fiscal_year,
            office,
            include_judges,
            limit,
            offset,
        )
        return shaped(payload, response_format, title="Judge movements")
