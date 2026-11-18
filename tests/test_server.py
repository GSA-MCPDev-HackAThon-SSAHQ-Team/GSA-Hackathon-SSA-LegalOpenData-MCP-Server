"""End-to-end through the MCP protocol (in-memory client)."""

from __future__ import annotations

import pytest
from fastmcp import Client

from ssa_alj_mcp.app import mcp


def _data(result):
    sc = result.structured_content
    if isinstance(sc, dict) and "result" in sc and len(sc) == 1:
        return sc["result"]
    return sc


EXPECTED_TOOLS = {
    "ssa_alj_list_reports",
    "ssa_alj_search_judges",
    "ssa_alj_get_judge_profile",
    "ssa_alj_compare_offices",
    "ssa_alj_get_office_profile",
    "ssa_alj_office_processing_ranking",
    "ssa_alj_national_trend",
    "ssa_alj_monthly_pace",
    "ssa_alj_compare_periods",
    "ssa_alj_outlier_report",
    "ssa_alj_within_office_variation",
    "ssa_alj_judge_movements",
    "ssa_alj_data_quality_notes",
}


@pytest.fixture
async def client(db_path):
    async with Client(mcp) as c:
        yield c


async def test_tools_listed_read_only(client):
    tools = await client.list_tools()
    assert {t.name for t in tools} == EXPECTED_TOOLS
    assert all(t.annotations and t.annotations.readOnlyHint for t in tools)


async def test_call_tool(client):
    result = await client.call_tool(
        "ssa_alj_get_office_profile", {"office": "miami", "fiscal_year": 2024}
    )
    assert _data(result)["office"] == "MIAMI"


async def test_invalid_arguments_rejected(client):
    with pytest.raises(Exception):
        await client.call_tool("ssa_alj_compare_offices", {"as_of": "'; DROP TABLE alj;--"})


async def test_resource_and_prompts(client):
    res = await client.read_resource("ssa-alj://about")
    assert "cumulative" in res[0].text
    assert {p.name for p in await client.list_prompts()} == {
        "compare_office_outcomes",
        "judge_summary",
    }
