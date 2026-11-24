"""ssa_alj_source_links — SSA HTML/XML URLs for verifying published figures."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from ssa_alj_mcp.models import FiscalYear, PaginationParams, PeriodEnd, ResponseFormat
from ssa_alj_mcp.services import discovery
from ssa_alj_mcp.tools._common import (
    DISCOVERY,
    ResponseFormatParam,
    annotations,
    page_args,
    shaped,
    tool_group,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="ssa_alj_source_links",
        **tool_group(DISCOVERY),
        annotations=annotations("SSA source HTML/XML links for a report snapshot"),
    )
    async def ssa_alj_source_links(
        fiscal_year: FiscalYear | None = None,
        as_of: PeriodEnd | None = None,
        report_kind: Annotated[
            Literal["disposition", "ranking", "both"],
            Field(
                description=(
                    "Which SSA report family: disposition (allowance/decisions), ranking "
                    "(dispositions per day per ALJ), or both. Default disposition."
                )
            ),
        ] = "disposition",
        pagination: PaginationParams | None = None,
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """SSA website HTML/XML links so a human can verify figures on ssa.gov.

        Call after a ranking or disposition tool. Prefer as_of when you have an exact period end;
        otherwise pass fiscal_year for that year's FY-final disposition file. Snapshot-scoped
        tools may also embed sources under snapshot.sources.
        """
        limit, offset = page_args(pagination)
        payload = await asyncio.to_thread(
            discovery.source_links, fiscal_year, as_of, report_kind, limit, offset
        )
        return shaped(payload, response_format, title="SSA ALJ source links")
