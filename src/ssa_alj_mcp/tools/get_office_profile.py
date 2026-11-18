"""ssa_alj_get_office_profile — one hearing office over time."""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP

from ssa_alj_mcp.models import FiscalYear, OfficeQuery, ResponseFormat
from ssa_alj_mcp.services import offices
from ssa_alj_mcp.tools._common import ResponseFormatParam, annotations, refusal_for, shaped


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="ssa_alj_get_office_profile",
        annotations=annotations("Multi-year disposition profile for one hearing office"),
    )
    async def ssa_alj_get_office_profile(
        office: OfficeQuery,
        fiscal_year: FiscalYear | None = None,
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """Multi-year disposition totals for one hearing office (name variants merged by city).

        Pass fiscal_year to include that year's judges. For a cross-office ranking in one year,
        use ssa_alj_compare_offices.
        """
        if refused := refusal_for(office):
            return shaped(refused, response_format, title="Request refused")
        payload = await asyncio.to_thread(offices.get_office_profile, office, fiscal_year)
        return shaped(payload, response_format, title=f"Office profile: {office}")
