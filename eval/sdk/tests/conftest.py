"""Configure mcpevals agent + skip when no LLM API key is present."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

SDK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SDK_ROOT.parents[1]


def _has_llm_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"))


def pytest_configure(config: pytest.Config) -> None:
    # Ensure config discovery finds mcp-agent.config.yaml next to this package.
    os.chdir(SDK_ROOT)


@pytest.fixture(scope="session")
def llm_available() -> bool:
    return _has_llm_key()


@pytest.fixture(autouse=True)
def _require_llm_for_agent_tests(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("mcp_eval") and not _has_llm_key():
        pytest.skip("Set ANTHROPIC_API_KEY or OPENAI_API_KEY to run mcpevals agent cases")


@pytest.fixture(scope="session", autouse=True)
def _configure_mcp_eval() -> None:
    """Load AgentSpec + pick provider from whichever key is available."""
    # Import only after chdir so mcp-agent finds local YAML.
    import mcp_eval
    from mcp_agent.agents.agent_spec import AgentSpec
    from mcp_eval.config import get_settings, load_config, use_agent

    load_config()
    settings = get_settings()

    if os.getenv("ANTHROPIC_API_KEY"):
        settings.provider = "anthropic"
        settings.model = getattr(settings, "model", None) or "claude-3-5-haiku-20241022"
    elif os.getenv("OPENAI_API_KEY"):
        settings.provider = "openai"
        settings.model = "gpt-4o-mini"

    # Point DB at the shipped SQLite even if the child inherits a weird cwd.
    os.environ.setdefault("SSA_ALJ_DB_PATH", str(REPO_ROOT / "data" / "ssa_alj.sqlite"))

    instruction = (
        "You evaluate the SSA ALJ Open Data MCP server. Prefer its tools for factual "
        "questions about hearing offices, judges, trends, and source links. Counts are "
        "fiscal-year-to-date; September is the full year. Allowance rates are not "
        "case-mix adjusted and are not performance ratings. Do not forecast future "
        "rates or name a best-performing judge. Cite report as-of dates and offer "
        "ssa_alj_source_links (or snapshot.sources) so users can verify on ssa.gov."
    )
    use_agent(
        AgentSpec(
            name="ssa_alj_tester",
            instruction=instruction,
            server_names=["ssa_alj"],
        )
    )
    # Touch mcp_eval so setup hooks from decorator style remain available if mixed later.
    _ = mcp_eval
