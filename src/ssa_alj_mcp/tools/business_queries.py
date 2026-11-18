"""ssa_alj_business_queries — curated analyst questions and custom query plans."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ssa_alj_mcp.models import PaginationParams, ResponseFormat
from ssa_alj_mcp.services import discovery
from ssa_alj_mcp.tools._common import ResponseFormatParam, annotations, page_args, shaped


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="ssa_alj_business_queries",
        annotations=annotations("List or match curated SSA ALJ business questions"),
    )
    async def ssa_alj_business_queries(
        query: Annotated[
            str | None,
            Field(
                description=(
                    "Optional free-text business question. Omit to list the curated catalog. "
                    "When set, returns the closest catalog recipes (tools + args), not answers."
                ),
                max_length=500,
            ),
        ] = None,
        category: Annotated[
            str | None,
            Field(
                description=(
                    "Optional catalog filter: coverage | offices | judges | trends | "
                    "ranking | quality. Ignored when matching a custom query."
                ),
                max_length=40,
            ),
        ] = None,
        pagination: PaginationParams | None = None,
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """Curated business questions, or a tool plan for a custom question.

        Use with no query to browse recipes an analyst can run. Pass a custom question to get
        suggested tools and args — then call those tools (and ssa_alj_source_links) for numbers
        and verification URLs. This tool does not compute disposition statistics itself.
        """
        limit, offset = page_args(pagination)
        payload = await asyncio.to_thread(
            discovery.business_queries, query, category, limit, offset
        )
        return shaped(payload, response_format, title="SSA ALJ business queries")
