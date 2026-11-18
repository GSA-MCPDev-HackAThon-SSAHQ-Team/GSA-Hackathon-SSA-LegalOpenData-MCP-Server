# SSA ALJ Open Data MCP Server

MCP (Model Context Protocol) server over **public** SSA Office of Hearings Operations
Administrative Law Judge disposition data (fiscal years 2010–2026).

Built for the [GSA MCP Server & SI Agent Government Hackathon](https://www.gsa.gov/super-intelligence/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon)
(Dataset Access Server). Layout follows the
[GSA-TTS/mcp-hackathon-template](https://github.com/GSA-TTS/mcp-hackathon-template).

## Problem

SSA publishes ALJ disposition counts as dozens of XML snapshots on
[ssa.gov](https://www.ssa.gov/appeals/DataSets/) (Data.gov collection `US-GOV-SSA-1199`), but the
files are cumulative fiscal-year-to-date, schemas drift, office names change, and there is no judge
ID. An LLM cannot safely answer “how did allowance rates change?” by scraping those files alone.

## Solution

This server is a **read-only MCP translation layer**: 15 tools, one resource, two prompts over a
local SQLite database built from those public files. Agents call tools; they never need to know
XML layout or FYTD semantics.

| Layer | Role |
|---|---|
| **Tools** | Structured queries (JSON or Markdown) |
| **Resource** | `ssa-alj://about` — data dictionary |
| **Prompts** | `compare_office_outcomes`, `judge_summary` |
| **Transports** | stdio (local clients) · streamable-HTTP (`/mcp`) for remote |

## Tools

| Tool | Answers |
|---|---|
| `ssa_alj_list_reports` | Coverage and “as of” dates |
| `ssa_alj_business_queries` | Curated analyst questions or a plan for a custom question |
| `ssa_alj_source_links` | SSA HTML/XML URLs to verify figures on ssa.gov |
| `ssa_alj_search_judges` | Published judge name |
| `ssa_alj_get_judge_profile` | One judge vs national rates |
| `ssa_alj_compare_offices` | Rank offices for a fiscal year |
| `ssa_alj_get_office_profile` | One office over time |
| `ssa_alj_office_processing_ranking` | SSA National Ranking report |
| `ssa_alj_national_trend` | National/regional series since FY2010 |
| `ssa_alj_monthly_pace` | Within-year pace (differenced snapshots) |
| `ssa_alj_compare_periods` | Biggest movers between two years |
| `ssa_alj_outlier_report` | Peer z-score outliers (not case-mix adjusted) |
| `ssa_alj_within_office_variation` | Judge spread inside an office |
| `ssa_alj_judge_movements` | Headcount and office moves |
| `ssa_alj_data_quality_notes` | Gaps and what the data does not contain |

All tools are annotated read-only / idempotent. List tools paginate
(`total` / `count` / `offset` / `has_more` / `next_offset` / `items`) and include a `notes` array.
Successful payloads that use one snapshot expose `snapshot: {period_end, fiscal_year, report}`.
Pass `response_format: "markdown"` for a human-readable summary.

## How to run

```bash
uv sync
# data/ssa_alj.sqlite is in the repo for Docker/Render. To rebuild from SSA XML:
# uv run --group etl scripts/crawl_ssa_alj.py && uv run scripts/load_ssa_alj.py

uv run pytest -q
uv run ssa-alj-mcp                                          # stdio
MCP_TRANSPORT=streamable-http uv run ssa-alj-mcp            # http://127.0.0.1:8000/mcp
```

- Protocol walkthrough: `uv run python scripts/mcp_client_demo.py`
- Inspector: `npx @modelcontextprotocol/inspector .venv/bin/ssa-alj-mcp`
- Local clients: [docs/LOCAL_STDIO_SETUP.md](docs/LOCAL_STDIO_SETUP.md) (Goose, Claude Desktop)
- ChatGPT (remote URL): [docs/CHATGPT_SETUP.md](docs/CHATGPT_SETUP.md)
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Evaluation results: [eval/RESULTS.md](eval/RESULTS.md)
- Docker smoke: [docs/DOCKER_SMOKE.md](docs/DOCKER_SMOKE.md)
- Protocol eras: [docs/PROTOCOL.md](docs/PROTOCOL.md)

## Security posture

- Public SSA statistics only (judge names as published; no claimant data).
- Database opened read-only (`mode=ro`, `PRAGMA query_only`); parameterised SQL only.
- No outbound network calls from the server process.
- `/mcp` is unauthenticated by default (hackathon public-data posture — see `SECURITY.md`).
- `/health` reports `db_ok` so hosts can detect a missing database.

## Project layout

```
src/ssa_alj_mcp/     FastMCP app, tools/, services/, resources/, prompts/
tests/               pytest (synthetic DB + MCP protocol tests)
db/schema.sql        SQLite schema + views
scripts/             Offline ETL (crawl + load) — not part of MCP runtime
eval/                Deterministic eval harness + RESULTS.md
docs/                architecture, client setup, Docker smoke, protocol
Dockerfile           streamable-HTTP image (copies data/ssa_alj.sqlite when present)
```

## Data provenance

Source XML: https://www.ssa.gov/appeals/DataSets/ · Catalog: Data.gov `US-GOV-SSA-1199`.
Counts are **cumulative fiscal-year-to-date** (federal FY Oct–Sep); the September snapshot is the
full year. Rates are **not** case-mix adjusted.
