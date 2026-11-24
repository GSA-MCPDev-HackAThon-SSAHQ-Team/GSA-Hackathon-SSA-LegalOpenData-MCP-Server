"""ssa_alj_data_quality_notes — known gaps and out-of-scope notes."""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP

from ssa_alj_mcp.models import ResponseFormat
from ssa_alj_mcp.services import quality
from ssa_alj_mcp.tools._common import (
    DISCOVERY,
    ResponseFormatParam,
    annotations,
    shaped,
    tool_group,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="ssa_alj_data_quality_notes",
        **tool_group(DISCOVERY),
        annotations=annotations("Dataset gaps, anomalies, and what is not published"),
    )
    async def ssa_alj_data_quality_notes(
        response_format: ResponseFormatParam = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """Gaps, load anomalies, and what this dataset does not contain.

        Call before claiming something is missing, or when answering out-of-scope questions
        (wait times, case mix, bias). See also ssa-alj://about.
        """
        payload = await asyncio.to_thread(quality.data_quality_notes)
        return shaped(payload, response_format, title="Data quality notes")
