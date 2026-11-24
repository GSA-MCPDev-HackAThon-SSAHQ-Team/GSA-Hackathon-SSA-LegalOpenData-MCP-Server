# Docs

Project documentation for the SSA ALJ Open Data MCP server.

| Doc | Topic |
|---|---|
| [demo/demo.md](demo/demo.md) | Live demo URLs, 5‑minute flow, sample prompts |
| [demo/SSA-ALJ-MCP-Hackathon-Deck.pptx](demo/SSA-ALJ-MCP-Hackathon-Deck.pptx) | Hackathon presentation deck (sample template filled for SSA ALJ) |
| [demo/SSA-ALJ-MCP-Evaluation-Document.docx](demo/SSA-ALJ-MCP-Evaluation-Document.docx) | Evaluation documentation deliverable (methodology → lessons) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Package layout, tools, data model, transports |
| [ssa-alj-mcp-roles.svg](ssa-alj-mcp-roles.svg) | MCP Host · Client · Server building blocks |
| [ssa-alj-mcp-architecture.svg](ssa-alj-mcp-architecture.svg) | MCP hosts ↔ server ↔ SQLite |
| [ssa-alj-data-prep-flow.svg](ssa-alj-data-prep-flow.svg) | Offline crawl/load → how SQLite is maintained |
| [EVALUATION.md](EVALUATION.md) | Criterion 2 — what each eval is |
| [../eval/RESULTS.md](../eval/RESULTS.md) | Recorded scores + external eval screenshots |
| [LEARNINGS.md](LEARNINGS.md) | MCPJam agent-eval notes and the open failed iterations |
| [CODEMAP.md](CODEMAP.md) | Where to change X |
| [LOCAL_STDIO_SETUP.md](LOCAL_STDIO_SETUP.md) | Goose / Claude Desktop |
| [CHATGPT_SETUP.md](CHATGPT_SETUP.md) | Remote HTTPS `/mcp` for ChatGPT |
| [DOCKER_SMOKE.md](DOCKER_SMOKE.md) | Container smoke test |
| [PROTOCOL.md](PROTOCOL.md) | MCP protocol eras |

---

# MCP Tools — SSA ALJ Open Data Server

This server exposes **15** read-only tools over SSA Administrative Law Judge (ALJ) disposition data,
fiscal years 2010-2026. Each tool carries FastMCP `tags` / `meta.category`
(`discovery` | `lookup` | `analysis`). Architecture: [ARCHITECTURE.md](ARCHITECTURE.md). Docker:
[DOCKER_SMOKE.md](DOCKER_SMOKE.md). Protocol eras: [PROTOCOL.md](PROTOCOL.md). Tool code lives in
`src/ssa_alj_mcp/tools/` (one file per tool).

## Discovery — orient and verify

| Tool | Key inputs | Answers |
|---|---|---|
| `ssa_alj_list_reports` | `fiscal_year?` | What data exists, and what "as of" date does a number carry? |
| `ssa_alj_business_queries` | `query?`, `category?` | Curated analyst questions, or a tool plan for custom text |
| `ssa_alj_source_links` | `year?`, `as_of?`, `kind?` | SSA HTML/XML URLs to verify figures on ssa.gov |
| `ssa_alj_data_quality_notes` | none | What is missing, anomalous, or not in the data? |

## Lookup — look things up

| Tool | Key inputs | Answers |
|---|---|---|
| `ssa_alj_search_judges` | `name`, `office?`, `fiscal_year?` | Which judge, and which published spelling, is this? |
| `ssa_alj_get_judge_profile` | `name`, `fiscal_year?` | One judge's decisions and rates by year, next to the national rate |
| `ssa_alj_compare_offices` | `fiscal_year?`, `region?`, `min_decisions`, `sort_by` | Which offices are highest or lowest on a measure? |
| `ssa_alj_get_office_profile` | `office`, `fiscal_year?` | One office over time, plus its judges |
| `ssa_alj_office_processing_ranking` | `period_end?`, `region?` | SSA's National Ranking report (dispositions per day per ALJ) |

## Analysis — derive insight

| Tool | Key inputs | Answers |
|---|---|---|
| `ssa_alj_national_trend` | `group_by`, `region?`, `from/to_fiscal_year` | How have outcomes, volume and judge headcount changed since 2010? |
| `ssa_alj_monthly_pace` | `fiscal_year?`, `office?`, `region?` | Is output speeding up or slowing down this year? |
| `ssa_alj_compare_periods` | `entity`, two fiscal years, `name?` | What changed most between two years? |
| `ssa_alj_outlier_report` | `level`, `measure`, `min_decisions?`, `min_z` | Which offices or judges sit far from their peers? |
| `ssa_alj_within_office_variation` | `office?`, `region?`, `min_judges` | How much do judges differ within one office? |
| `ssa_alj_judge_movements` | two fiscal years, `office?` | Where did judges join, leave or change office? |

## Also exposed

- **Resource:** `ssa-alj://about` (data dictionary, tool groups, and caveats).
- **Prompts:** `compare_office_outcomes`, `judge_summary`.
- **HTTP routes** (HTTP transport only): `GET /health`, `GET /version`, MCP endpoint `/mcp`.

## How to read the results

- Counts are **cumulative fiscal-year-to-date**; the September snapshot is the full year.
- Judges are matched by **published name only** (SSA publishes no judge ID).
- Rates are **not adjusted for case mix**; outlier and variation results are descriptive, not
  evidence of error or poor performance.
- Snapshot tools may embed SSA URLs under `snapshot.sources`; `ssa_alj_source_links` is the
  dedicated verification tool when you need links without a ranking payload.
