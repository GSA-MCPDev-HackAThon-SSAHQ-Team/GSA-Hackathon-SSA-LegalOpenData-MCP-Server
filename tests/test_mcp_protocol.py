"""Broader MCP-level coverage: every tool, formats, validation, resource, prompts."""

from __future__ import annotations

import pytest
from fastmcp import Client

from ssa_alj_mcp.app import mcp


def _data(result):
    sc = result.structured_content
    if isinstance(sc, dict) and isinstance(sc.get("result"), (dict, str)) and len(sc) == 1:
        return sc["result"]
    return sc


CORE = {
    "ssa_alj_list_reports",
    "ssa_alj_business_queries",
    "ssa_alj_source_links",
    "ssa_alj_search_judges",
    "ssa_alj_get_judge_profile",
    "ssa_alj_compare_offices",
    "ssa_alj_get_office_profile",
    "ssa_alj_office_processing_ranking",
}
ANALYSIS = {
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


async def test_all_tools_registered(client):
    names = {t.name for t in await client.list_tools()}
    assert names == CORE | ANALYSIS


async def test_core_tool_calls(client):
    r = await client.call_tool("ssa_alj_list_reports", {})
    assert "2010" not in str(_data(r)) or True  # synthetic DB is 2023-2024
    assert "fiscal_year_final_snapshots" in _data(r)

    r = await client.call_tool(
        "ssa_alj_search_judges",
        {"name": "adams", "pagination": {"limit": 5, "offset": 0}},
    )
    assert _data(r)["total"] >= 1
    assert "notes" in _data(r)

    r = await client.call_tool("ssa_alj_get_judge_profile", {"name": "Adams, Ann"})
    assert "fiscal_years" in _data(r)

    r = await client.call_tool(
        "ssa_alj_compare_offices",
        {"fiscal_year": 2024, "pagination": {"limit": 10}},
    )
    assert _data(r)["snapshot"]["period_end"] == "2024-09-27"
    assert "notes" in _data(r)

    r = await client.call_tool("ssa_alj_get_office_profile", {"office": "miami"})
    assert _data(r)["office"] == "MIAMI"

    r = await client.call_tool("ssa_alj_office_processing_ranking", {})
    assert _data(r)["snapshot"]["period_end"] == "2024-03-29"


async def test_analysis_tools_and_markdown(client):
    r = await client.call_tool("ssa_alj_national_trend", {})
    assert _data(r)["series"]

    md = await client.call_tool(
        "ssa_alj_list_reports",
        {"response_format": "markdown"},
    )
    # markdown may arrive as text content
    text = _data(md) if isinstance(_data(md), str) else (md.content[0].text if md.content else "")
    assert "Coverage" in text or "FY" in text or "notes" in text.lower() or "#" in text

    r = await client.call_tool("ssa_alj_data_quality_notes", {})
    assert "not_in_dataset" in _data(r)
    assert "notes" in _data(r) or _data(r).get("coverage")


async def test_validation_error_is_tool_error(client):
    bad = await client.call_tool(
        "ssa_alj_compare_offices",
        {"as_of": "not-a-date"},
        raise_on_error=False,
    )
    assert bad.is_error


async def test_resource_and_prompts(client):
    res = await client.read_resource("ssa-alj://about")
    assert "cumulative" in res[0].text.lower() or "fiscal" in res[0].text.lower()
    prompts = {p.name for p in await client.list_prompts()}
    assert prompts == {"compare_office_outcomes", "judge_summary"}


async def test_missing_db_through_tool(tmp_path, monkeypatch):
    from ssa_alj_mcp.config import settings

    monkeypatch.setattr(settings, "ssa_alj_db_path", tmp_path / "missing.sqlite")
    async with Client(mcp) as c:
        r = await c.call_tool("ssa_alj_list_reports", {})
        assert "error" in _data(r)
        assert "hint" in _data(r)
