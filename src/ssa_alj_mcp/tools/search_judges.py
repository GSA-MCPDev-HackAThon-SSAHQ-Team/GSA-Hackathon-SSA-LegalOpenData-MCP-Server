"""ssa_alj_search_judges — find a published ALJ name."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ssa_alj_mcp.models import FiscalYear, JudgeNameQuery, PaginationParams, ResponseFormat
from ssa_alj_mcp.services import judges
from ssa_alj_mcp.tools._common import (
    ResponseFormatParam,
    annotations,
    page_args,
    refusal_for,
    shaped,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="ssa_alj_search_judges",
        annotations=annotations("Find the published spelling of an ALJ name"),
    )
    async def ssa_alj_search_judges(
        name: JudgeNameQuery,
        office: Annotated[
            str | None,
            Field(
                description=(
                    "Optional hearing office filter; every word must appear in the office name. "
                    "Example: 'Miami'."
                ),
                max_length=100,
            ),
        ] = None,
        fiscal_year: FiscalYear | None = None,
        pagination: PaginationParams | None = None,
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """Search published ALJ names (SSA has no judge IDs).

        Use this to confirm spelling before ssa_alj_get_judge_profile when the name might match
        more than one person.
        """
        if refused := refusal_for(name, office):
            return shaped(refused, response_format, title="Request refused")
        limit, offset = page_args(pagination)
        payload = await asyncio.to_thread(
            judges.search_judges, name, office, fiscal_year, limit, offset
        )
        return shaped(payload, response_format, title=f"Judges matching '{name}'")
