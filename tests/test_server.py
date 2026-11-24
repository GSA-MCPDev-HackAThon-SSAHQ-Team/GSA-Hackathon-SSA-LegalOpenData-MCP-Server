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
    "ssa_alj_business_queries",
    "ssa_alj_source_links",
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


TOOL_GROUPS = {
    "ssa_alj_list_reports": "discovery",
    "ssa_alj_business_queries": "discovery",
    "ssa_alj_source_links": "discovery",
    "ssa_alj_data_quality_notes": "discovery",
    "ssa_alj_search_judges": "lookup",
    "ssa_alj_get_judge_profile": "lookup",
    "ssa_alj_compare_offices": "lookup",
    "ssa_alj_get_office_profile": "lookup",
    "ssa_alj_office_processing_ranking": "lookup",
    "ssa_alj_national_trend": "analysis",
    "ssa_alj_monthly_pace": "analysis",
    "ssa_alj_compare_periods": "analysis",
    "ssa_alj_outlier_report": "analysis",
    "ssa_alj_within_office_variation": "analysis",
    "ssa_alj_judge_movements": "analysis",
}


async def test_tools_listed_read_only(client):
    tools = await client.list_tools()
    assert {t.name for t in tools} == EXPECTED_TOOLS
    assert all(t.annotations and t.annotations.readOnlyHint for t in tools)


async def test_tools_carry_group_tags(client):
    tools = {t.name: t for t in await client.list_tools()}
    assert set(tools) == EXPECTED_TOOLS
    for name, category in TOOL_GROUPS.items():
        meta = tools[name].meta or {}
        assert meta.get("category") == category, name
        tags = (meta.get("fastmcp") or {}).get("tags") or []
        assert category in tags, name


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
    text = res[0].text
    assert "cumulative" in text
    assert "discovery:" in text and "lookup:" in text and "analysis:" in text
    assert "not adjusted for case mix" in text
    assert "ssa_alj_business_queries" in text and "ssa_alj_source_links" in text
    assert {p.name for p in await client.list_prompts()} == {
        "compare_office_outcomes",
        "judge_summary",
    }
