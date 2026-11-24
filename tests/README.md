# Tests

CI safety net for the MCP server. **pytest only** — no LLM agent-eval SDK here.
Optional **`mcpevals`** agent suite lives under [`eval/sdk/`](../eval/sdk/) (nested project).
Gold / MCPJam evidence: [`eval/`](../eval/).

```bash
uv run pytest -q
```

Uses a **synthetic SQLite** built in `conftest.py` from `data/db/schema.sql` (no network, no real `data/ssa_alj.sqlite`), except one optional check that reads the shipped DB when present.

## Files

| File | Covers |
|---|---|
| `conftest.py` | Tiny in-memory-style fixture DB + path monkeypatch |
| `test_utils.py` | Normalize / paginate / rate / error helpers |
| `test_formatting_health.py` | Markdown shaping, `/` landing + `/health` |
| `test_services.py` | Lookup services (reports, judges, offices, ranking) |
| `test_analytics.py` | Trends, outliers, movements, quality notes (+ optional real-DB smoke) |
| `test_discovery.py` | Business queries, source links, scope notes |
| `test_guardrails.py` | Refusal / PII / security probes; no echo of matched text |
| `test_server.py` | In-memory MCP client: tool list, group tags, smoke call |
| `test_mcp_protocol.py` | Broader MCP: all tools, markdown, validation, resource/prompts, missing DB |

## Eval SDK?

**None.** These tests call package code and FastMCP’s in-process `Client`. Criterion 2 scoring (gold cases, latency, external host suites) is documented in [`eval/README.md`](../eval/README.md).
