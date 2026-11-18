"""Formatting helpers, office aliases, and /health DB probe."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from ssa_alj_mcp.app import mcp
from ssa_alj_mcp.formatting import ensure_notes, to_markdown
from ssa_alj_mcp.office_aliases import canonical_office


def test_canonical_office_aliases():
    assert canonical_office("HOUSTON-BISSONNET") == "HOUSTON WEST"
    assert canonical_office("PHOENIX") == "PHOENIX DOWNTOWN"
    assert canonical_office("WEST DES MOINES") == "DES MOINES"
    assert canonical_office("MIAMI") == "MIAMI"


def test_ensure_notes_and_markdown_error():
    assert ensure_notes({"a": 1}, "n1")["notes"] == ["n1"]
    assert "error" in to_markdown({"error": "boom", "hint": "try x"}).lower()


def test_markdown_list():
    text = to_markdown(
        {
            "snapshot": {"period_end": "2024-09-27", "fiscal_year": 2024, "report": "September"},
            "items": [{"office": "MIAMI", "allowance_rate": 0.6}],
            "total": 1,
            "notes": ["Cumulative FYTD."],
        },
        title="Test",
    )
    assert "MIAMI" in text and "As of 2024-09-27" in text


@pytest.mark.asyncio
async def test_home_shows_request_mcp_url(db_path):
    app = mcp.http_app()
    transport = TestClient(app)
    res = transport.get("/", headers={"host": "mcp.example.com", "x-forwarded-proto": "https"})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert ">https://mcp.example.com/mcp</code>" in res.text
    assert 'href="https://mcp.example.com/health"' in res.text
    assert "ssa_alj_list_reports" in res.text
    assert "List FY coverage" in res.text
    assert "<h1>SSA Administrative Law Judge (ALJ) Open Data</h1>" in res.text


@pytest.mark.asyncio
async def test_health_db_ok(db_path):
    # Build a minimal ASGI app from FastMCP custom routes via http_app if available.
    app = mcp.http_app()
    transport = TestClient(app)
    res = transport.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["db_ok"] is True
    assert body["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_db_missing(tmp_path, monkeypatch):
    from ssa_alj_mcp.config import settings

    monkeypatch.setattr(settings, "ssa_alj_db_path", tmp_path / "nope.sqlite")
    app = mcp.http_app()
    transport = TestClient(app)
    res = transport.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["db_ok"] is False
    assert body["status"] == "degraded"
