# Code map — where to change X

One-page guide for skimming the repo. Runtime MCP code lives under `src/ssa_alj_mcp/`; ETL is offline under `scripts/`.

## Want to…

| Change | Look here |
|---|---|
| Add / edit an MCP tool | `src/ssa_alj_mcp/tools/core/` or `tools/analysis/` (one file each); register in `tools/__init__.py`; see [AGENT_TOOLS.md](AGENT_TOOLS.md) |
| Change query logic / SQL | Matching module under `src/ssa_alj_mcp/services/` (tools stay thin wrappers) |
| Shared disposition `SUM(...)` SQL | `src/ssa_alj_mcp/services/sql.py` |
| Snapshot resolution / rates / FY notes | `src/ssa_alj_mcp/services/common.py` |
| Pagination / error dict / name key | `src/ssa_alj_mcp/utils.py` |
| JSON vs Markdown shaping | `src/ssa_alj_mcp/formatting.py` |
| Tool input types (`FiscalYear`, pagination) | `src/ssa_alj_mcp/models.py` |
| FastMCP app, transport, `/health` | `src/ssa_alj_mcp/app.py`, `routes.py`, `config.py` |
| Resource / prompts | `src/ssa_alj_mcp/resources/`, `prompts/` |
| Office name aliases (Houston West, etc.) | `src/ssa_alj_mcp/office_aliases.py` |
| Schema / views | `db/schema.sql` |
| Crawl SSA XML / load SQLite | `scripts/crawl_ssa_alj.py`, `scripts/load_ssa_alj.py` (**offline ETL**, not MCP runtime) |
| Tests | `tests/` (synthetic DB fixtures in `conftest.py`) |
| Evaluation / Criterion 2 | [EVALUATION.md](EVALUATION.md) (what each eval is) → `eval/RESULTS.md` (scores); code in `eval/deterministic/`, `eval/phoenix/` |
| Client / Docker / protocol docs | `docs/` |

## Layering (do not blur)

```
tools/          → async MCP surface; never import sqlite3
services/       → sync query logic + SQL
utils.py        → pure helpers (no DB)
formatting.py   → response shaping for MCP
scripts/        → offline ETL pipeline only
```

## Core vs analysis tools

Matches the README tables: lookup tools under `tools/core/`; trend/diagnostic tools under `tools/analysis/`.
