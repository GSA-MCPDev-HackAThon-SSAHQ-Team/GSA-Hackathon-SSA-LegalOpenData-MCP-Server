"""Offline checks — no LLM key required."""

from __future__ import annotations

from pathlib import Path

import yaml

SDK_ROOT = Path(__file__).resolve().parents[1]


def test_mcp_agent_config_declares_ssa_alj_stdio_server() -> None:
    data = yaml.safe_load((SDK_ROOT / "mcp-agent.config.yaml").read_text())
    server = data["mcp"]["servers"]["ssa_alj"]
    assert server["transport"] == "stdio"
    assert server["command"] == "uv"
    assert "ssa-alj-mcp" in server["args"]
    assert data.get("provider") in {"anthropic", "openai"}


def test_repo_sqlite_present_for_agent_runs() -> None:
    db = SDK_ROOT.parents[1] / "data" / "ssa_alj.sqlite"
    assert db.is_file(), f"expected shipped DB at {db}"
