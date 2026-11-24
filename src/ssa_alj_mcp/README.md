# `ssa_alj_mcp`

FastMCP package that exposes SSA ALJ disposition open data as MCP tools, resources, and prompts. Entry point: `app.py` (builds the server, registers parts, picks stdio or HTTP).

## Folders

| Folder | Role |
|---|---|
| **`tools/`** | Thin MCP tool wrappers (one module per tool). Validate args, run guardrails, call a service, format the reply. Groups: `discovery`, `lookup`, `analysis` (via tags + `meta.category` in `_common.py`). |
| **`services/`** | Sync query logic and SQL against the read-only SQLite DB. Tools stay thin; business logic lives here (`reports`, `discovery`, `judges`, `offices`, `trends`, `analysis`, `workforce`, `quality`, plus shared `common` / `sql`). |
| **`resources/`** | Static MCP resources clients can read directly (e.g. `ssa-alj://about` data dictionary). |
| **`prompts/`** | Reusable prompt templates (conversation starters for common questions). |
| **`guardrails/`** | Free-text input rules: `refusal()` blocks unsafe/out-of-scope queries; `scope_note()` adds advisory notes (forecast / “best performer”). See `guardrails/README.md`. |

## Root modules

| File | Role |
|---|---|
| `app.py` | Server bootstrap: FastMCP instance, register tools/prompts/resources/routes, transport selection. |
| `config.py` | Settings from env / `.env` (DB path, transport, host/port). |
| `db.py` | Read-only SQLite connection (`mode=ro`); no writes, no outbound network. |
| `models.py` | Shared Pydantic types (pagination, response format, etc.). |
| `formatting.py` | JSON / markdown response shaping and caveat notes. |
| `routes.py` | HTTP-only routes (landing page, health, MCP URL helpers) for streamable-http deploy. |
| `office_aliases.py` | Hearing-office name normalization / merge helpers. |
| `utils.py` | Small shared helpers. |
| `logging_config.py` | Logging setup used by `app.py` and routes. |

## Request path (tools)

```
MCP client → tools/<name>.py → guardrails (if free text)
            → services/<domain>.py → db.py (SQLite ro)
            → formatting → response
```

ETL and the shipped DB live under repo `data/` (`data/scripts/`, `data/db/`, `data/ssa_alj.sqlite`), not in this package. Architecture overview: [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md).
