# Code map — where to change X

One-page guide for skimming the repo. Runtime MCP code lives under `src/ssa_alj_mcp/`; ETL is offline under `data/scripts/`.

## Want to…

| Change | Look here |
|---|---|
| Add / edit an MCP tool | `src/ssa_alj_mcp/tools/` (one file each) + `tool_group(...)` tags; register in `tools/__init__.py` |
| Change query logic / SQL | Matching module under `src/ssa_alj_mcp/services/` (tools stay thin wrappers) |
| Shared disposition `SUM(...)` SQL | `src/ssa_alj_mcp/services/sql.py` |
| Snapshot resolution / rates / FY notes | `src/ssa_alj_mcp/services/common.py` |
| Pagination / error dict / name key | `src/ssa_alj_mcp/utils.py` |
| JSON vs Markdown shaping | `src/ssa_alj_mcp/formatting.py` |
| Tool input types (`FiscalYear`, pagination) | `src/ssa_alj_mcp/models.py` |
| FastMCP app, transport, `/health` | `src/ssa_alj_mcp/app.py`, `routes.py`, `config.py` |
| Resource / prompts | `src/ssa_alj_mcp/resources/`, `prompts/` |
| Office name aliases (Houston West, etc.) | `src/ssa_alj_mcp/office_aliases.py` |
| Schema / views | `data/db/schema.sql` |
| Crawl SSA XML / load SQLite | `data/scripts/crawl_ssa_alj.py`, `data/scripts/load_ssa_alj.py` (**offline ETL**, not MCP runtime) |
| Tests | `tests/` (synthetic DB fixtures in `conftest.py`) |
| Evaluation / Criterion 2 | [EVALUATION.md](EVALUATION.md) → `eval/RESULTS.md`; code in `eval/deterministic/`, gold in `eval/gold/`, MCPJam in `eval/mcpjam/`, optional `mcpevals` in `eval/sdk/` |
| Hackathon judging map | [JUDGE_CRITERIA.md](../JUDGE_CRITERIA.md) (Criteria 1–3, innovation, mission, presentation) |
| Live demo script | [demo.md](demo.md) |
| Client / Docker / protocol docs | `docs/` |

## Layering (do not blur)

```
tools/          → async MCP surface; never import sqlite3
services/       → sync query logic + SQL
utils.py        → pure helpers (no DB)
formatting.py   → response shaping for MCP
data/scripts/   → offline ETL pipeline only
```

## Tool groups (`meta.category`)

Matches [docs/README.md](README.md) and `ssa-alj://about`: every tool file under `tools/` sets
`tags` + `meta.category` via `tool_group()` in `_common.py` —

| Group | Role |
|---|---|
| `discovery` | Coverage, recipes, source URLs, quality notes |
| `lookup` | Judges, offices, ranking |
| `analysis` | Trends, pace, outliers, variation, movements |
