# Eval SDK — `mcpevals`

In-repo **agent evaluation** of the SSA ALJ MCP server using
[LastMile `mcpevals`](https://github.com/lastmile-ai/mcp-eval) (pytest + `Expect.*`).

**Tests & recorded scores:** [`RESULTS.md`](RESULTS.md) (kept separate from [`../RESULTS.md`](../RESULTS.md)).

This is a **nested uv project** on purpose: `mcpevals` / `mcp-agent` still need
`mcp>=1.28,<2` (`mcp.server.fastmcp`), while the main server runs **FastMCP 4 / mcp 2.x**.
The agent runner lives here; the server under test is spawned via
`uv run --project <repo-root> ssa-alj-mcp` (stdio).

Unit / protocol tests stay in repo [`tests/`](../../tests/) (no LLM, always CI-safe).

## Setup

```bash
cd eval/sdk
uv sync
export ANTHROPIC_API_KEY=...   # preferred (matches MCPJam Claude runs)
# or: export OPENAI_API_KEY=...
# optional: cp mcp-agent.secrets.yaml.example mcp-agent.secrets.yaml
```

## Run

```bash
cd eval/sdk
uv run pytest -q                      # smoke always; agent cases skip without a key
uv run pytest -q -m mcp_eval          # agent cases only (needs a key)
uv run mcp-eval run tests/ -v         # mcpevals CLI + reports under test-reports/
```

Then update [`RESULTS.md`](RESULTS.md) with the new pass/fail table.

Config: [`mcp-agent.config.yaml`](mcp-agent.config.yaml).
