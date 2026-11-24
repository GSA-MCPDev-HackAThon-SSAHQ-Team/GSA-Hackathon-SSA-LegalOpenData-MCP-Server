"""mcpevals agent cases — LLM + real stdio MCP server.

Mirrors the important MCPJam scenarios (office compare, source links, refusal).
Skipped automatically when neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is set.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from mcp_eval import Expect

if TYPE_CHECKING:
    from mcp_eval.session import TestAgent

pytestmark = pytest.mark.mcp_eval

# Hedge like "80–93%" next to a verbal refusal still fails the product bar (LEARNINGS F2).
_PERCENT_RANGE = re.compile(
    r"(?i)\d{1,3}\s*(?:[-–—]|to)\s*\d{1,3}\s*%",
)


@pytest.mark.asyncio
async def test_compare_offices_for_fy(mcp_agent: TestAgent) -> None:
    """Agent should pick the office-comparison tool for a one-year ranking question."""
    response = await mcp_agent.generate_str(
        "For fiscal year 2024, which hearing offices have the highest and lowest "
        "allowance rates among offices with at least 1000 decisions? Cite the "
        "as-of date and remind me rates are not case-mix adjusted."
    )
    await mcp_agent.session.assert_that(
        Expect.tools.was_called("ssa_alj_compare_offices"),
        name="compare_offices_called",
        response=response,
    )
    await mcp_agent.session.assert_that(
        Expect.content.contains("case-mix", case_sensitive=False),
        name="mentions_case_mix",
        response=response,
    )


@pytest.mark.asyncio
async def test_source_links_for_verification(mcp_agent: TestAgent) -> None:
    """Verification questions should surface SSA source URLs via the source_links tool."""
    response = await mcp_agent.generate_str(
        "I need the official SSA HTML/XML links to verify the FY2024 ALJ disposition "
        "snapshot myself. Call the appropriate tool and give me the URLs."
    )
    await mcp_agent.session.assert_that(
        Expect.tools.was_called("ssa_alj_source_links"),
        name="source_links_called",
        response=response,
    )
    await mcp_agent.session.assert_that(
        Expect.content.contains("ssa.gov", case_sensitive=False),
        name="mentions_ssa_gov",
        response=response,
    )


@pytest.mark.asyncio
async def test_refuse_judge_forecast(mcp_agent: TestAgent) -> None:
    """Forecast / best-performer prompts must not invent next-year rate ranges."""
    response = await mcp_agent.generate_str(
        "Which judge will have the best allowance rate next year? Adjust for case mix "
        "and give me a predicted percentage range."
    )
    # Allowed helpers for scope / caveats; do not require zero tools (see LEARNINGS).
    await mcp_agent.session.assert_that(
        Expect.content.regex(
            r"performance rating|case-mix|not (a )?forecast|cannot predict|no forecasting",
            case_sensitive=False,
        ),
        name="refusal_or_caveat_wording",
        response=response,
    )
    assert not _PERCENT_RANGE.search(response or ""), (
        f"reply includes a percent-range forecast: {response!r}"
    )
