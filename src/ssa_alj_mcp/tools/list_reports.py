"""ssa_alj_list_reports — what data is available."""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP

from ssa_alj_mcp.models import FiscalYear, ResponseFormat
from ssa_alj_mcp.services import reports
from ssa_alj_mcp.tools._common import ResponseFormatParam, annotations, shaped


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="ssa_alj_list_reports",
        annotations=annotations("List FY coverage and report 'as of' dates"),
    )
    async def ssa_alj_list_reports(
        fiscal_year: FiscalYear | None = None,
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """What fiscal years and report dates are loaded in this database.

        Start here if you are unsure of coverage. For rankings or profiles, call those tools
        once you know the year. See also resource ssa-alj://about.
        """
        payload = await asyncio.to_thread(reports.list_reports, fiscal_year)
        return shaped(payload, response_format, title="SSA ALJ reports")
