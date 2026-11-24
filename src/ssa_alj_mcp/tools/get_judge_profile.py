"""ssa_alj_get_judge_profile — one judge across fiscal years."""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP

from ssa_alj_mcp.models import FiscalYear, JudgeNameQuery, ResponseFormat
from ssa_alj_mcp.services import judges
from ssa_alj_mcp.tools._common import (
    LOOKUP,
    ResponseFormatParam,
    annotations,
    refusal_for,
    shaped,
    tool_group,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="ssa_alj_get_judge_profile",
        **tool_group(LOOKUP),
        annotations=annotations("Year-by-year disposition profile for one ALJ"),
    )
    async def ssa_alj_get_judge_profile(
        name: JudgeNameQuery,
        fiscal_year: FiscalYear | None = None,
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """Year-by-year dispositions for one ALJ, with national allowance rate for context.

        Prefer ssa_alj_search_judges first if the name could be ambiguous. Published counts only —
        not a performance rating. Prompt: judge_summary.
        """
        if refused := refusal_for(name):
            return shaped(refused, response_format, title="Request refused")
        payload = await asyncio.to_thread(judges.get_judge_profile, name, fiscal_year)
        return shaped(payload, response_format, title=f"Judge profile: {name}")
