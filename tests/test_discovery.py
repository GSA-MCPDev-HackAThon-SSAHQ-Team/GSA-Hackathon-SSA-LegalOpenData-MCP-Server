"""Discovery services: business-query catalog and SSA source links."""

from __future__ import annotations

import pytest
from fastmcp import Client

from ssa_alj_mcp.app import mcp
from ssa_alj_mcp.services import discovery


def _data(result):
    sc = result.structured_content
    if isinstance(sc, dict) and isinstance(sc.get("result"), (dict, str)) and len(sc) == 1:
        return sc["result"]
    return sc


@pytest.fixture
async def client(db_path):
    async with Client(mcp) as c:
        yield c


def test_business_queries_catalog(db_path):
    out = discovery.business_queries()
    assert out["mode"] == "catalog"
    assert out["total"] >= 8
    assert "coverage" in out["categories"]
    assert all("tools" in item for item in out["items"])


def test_business_queries_custom_match(db_path):
    out = discovery.business_queries(
        query="highest allowance rate office fiscal year 2024 at least 1000 decisions"
    )
    assert out["mode"] == "custom"
    assert out["matches"]
    assert out["matches"][0]["id"] == "fy2024_top_allowance_office"
    assert any(t["name"] == "ssa_alj_compare_offices" for t in out["suggested_plan"])


def test_business_queries_bad_category(db_path):
    out = discovery.business_queries(category="not-a-category")
    assert "error" in out


def test_source_links_disposition_fy(db_path):
    out = discovery.source_links(fiscal_year=2024, report_kind="disposition")
    assert out["primary"]["period_end"] == "2024-09-27"
    assert out["primary"]["xml_url"] == "https://example.test/3.xml"
    assert out["primary"]["html_url"] == "https://example.test/3.html"
    assert out["datasets_index"].startswith("https://www.ssa.gov/")


def test_source_links_ranking(db_path):
    out = discovery.source_links(report_kind="ranking")
    assert out["primary"]["report_kind"] == "ranking"
    assert out["primary"]["period_end"] == "2024-03-29"


def test_source_links_bad_kind(db_path):
    out = discovery.source_links(report_kind="wait_times")
    assert "error" in out


def test_compare_offices_embeds_sources(db_path):
    from ssa_alj_mcp.services import offices

    out = offices.compare_offices(fiscal_year=2024, limit=5)
    assert out["snapshot"]["sources"]["xml"] == "https://example.test/3.xml"
    assert out["snapshot"]["sources"]["html"] == "https://example.test/3.html"


async def test_discovery_tools_via_mcp(client):
    r = await client.call_tool("ssa_alj_business_queries", {})
    body = _data(r)
    assert body["mode"] == "catalog"
    assert body["total"] >= 1

    r = await client.call_tool(
        "ssa_alj_source_links",
        {"fiscal_year": 2024, "report_kind": "disposition"},
    )
    body = _data(r)
    assert body["primary"]["html_url"].endswith(".html")
