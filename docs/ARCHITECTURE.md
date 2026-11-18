# Architecture — SSA ALJ Open Data MCP Server

A read-only MCP server that answers questions about SSA Administrative Law Judge (ALJ)
disposition data (fiscal years 2010-2026) from a local SQLite database.

## 1. System context

```
   data/ssa_alj.sqlite   (prebuilt SSA ALJ disposition data, FY2010-2026, ~311k rows)
            │
            │ opened READ-ONLY (mode=ro, PRAGMA query_only)
            ▼
 ┌────────────────────────────── MCP SERVER (src/ssa_alj_mcp) ─────────────────────────────────┐
 │                                                                                              │
 │   MCP clients                                                                                │
 │   ┌──────────────┐  stdio (local subprocess)      ┌──────────────────────────────────────┐   │
 │   │ Goose        │◄──────────────────────────────►│                                      │   │
 │   │ Claude Code  │                                │   FastMCP app  (app.py)              │   │
 │   │ Cursor       │  streamable-HTTP  /mcp         │                                      │   │
 │   │ MCP Inspector│◄──────────────────────────────►│   tools · resources · prompts        │   │
 │   │ ChatGPT      │  (Render / Docker / cloud.gov) │   + /health  /version                │   │
 │   └──────────────┘                                └──────────────────────────────────────┘   │
 └──────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Server components

```
 app.py  (thin: build FastMCP, register parts, choose transport)
  │
  ├── register_tools()      tools/  (13 async tools, one file each)
  │       │                                  - validate args (Pydantic Field constraints)
  │       │                                  - asyncio.to_thread(service_fn, ...)
  │       ▼
  │   services/             plain sync functions -> JSON-serialisable dicts / error dicts
  │       │   reports.py  judges.py  offices.py  trends.py  analysis.py  workforce.py
  │       │   quality.py  common.py (snapshot resolution, SUM SQL,
  │       │                                                    derived rates, @handled)
  │       ▼
  │   db.py                 read-only sqlite3 connection, parameterised queries only
  │       ▼
  │   data/ssa_alj.sqlite   tables + views (v_fy_final_snapshot, ...)
  │
  ├── register_resources()  resources/    ssa-alj://about   (data dictionary + caveats)
  ├── register_prompts()    prompts/      compare_office_outcomes, judge_summary
  ├── register_routes()     routes.py     GET /health, GET /version   (HTTP only)
  │
  ├── config.py             Settings (env / .env): MCP_TRANSPORT, MCP_HOST, MCP_PORT,
  │                         SSA_ALJ_DB_PATH, max_page_size
  ├── models.py             shared Pydantic types / aliases
  └── utils.py              paginate, error payloads, normalize_key, rate
```

### Transport selection (`app.main`)

```
 PORT set? ──yes──► HTTP on 0.0.0.0:$PORT                                (cloud hosts)
          │ no
          ▼
 MCP_TRANSPORT=streamable-http? ──yes──► HTTP on MCP_HOST:MCP_PORT      (local HTTP test)
          │ no
          ▼
        stdio                                                           (default, local clients)
```

## 3. Tools

List tools share `{total,count,offset,has_more,next_offset,items,notes}`; snapshot-scoped tools add `snapshot:{period_end,fiscal_year,report}`. Optional `response_format=markdown`.

All tools are read-only (`readOnlyHint=true`, `destructiveHint=false`, `idempotentHint=true`,
`openWorldHint=false`). List-style results use the envelope
`{total, count, offset, has_more, next_offset, items}`.

```
 REFERENCE ─ look things up
 ┌───────────────────────────────────┬──────────────────────────────────────────┬──────────────────────┐
 │ Tool (file in tools/)             │ Input                                    │ Answers              │
 ├───────────────────────────────────┼──────────────────────────────────────────┼──────────────────────┤
 │ ssa_alj_list_reports              │ fiscal_year?                             │ What data exists and │
 │                                   │                                          │ what "as of" date?   │
 │ ssa_alj_search_judges             │ name, office?, fiscal_year?, paging      │ Which judge /        │
 │                                   │                                          │ spelling is this?    │
 │ ssa_alj_get_judge_profile         │ name, fiscal_year?                       │ One judge by year    │
 │                                   │                                          │ vs national          │
 │ ssa_alj_compare_offices           │ fiscal_year?, as_of?, region?,           │ Highest / lowest     │
 │                                   │ min_decisions, sort_by, paging           │ offices on a measure │
 │ ssa_alj_get_office_profile        │ office, fiscal_year?                     │ One office over time │
 │                                   │                                          │ and its judges       │
 │ ssa_alj_office_processing_ranking │ period_end?, region?, paging             │ SSA's National       │
 │                                   │                                          │ Ranking report       │
 └───────────────────────────────────┴──────────────────────────────────────────┴──────────────────────┘

 ANALYSIS ─ derive insight
 ┌───────────────────────────────────┬──────────────────────────────────────────┬──────────────────────┐
 │ ssa_alj_national_trend            │ group_by (national|region), region?,     │ How did outcomes,    │
 │                                   │ from/to_fiscal_year                      │ volume, headcount    │
 │                                   │                                          │ change since 2010?   │
 │ ssa_alj_monthly_pace              │ fiscal_year?, office?, region?           │ Is output speeding   │
 │                                   │                                          │ up or slowing down?  │
 │ ssa_alj_compare_periods           │ entity (office|region|judge), FY a, FY b,│ What changed most    │
 │                                   │ name?, min_decisions, sort_by, direction │ between two years?   │
 │ ssa_alj_outlier_report            │ level (office|judge), measure, FY?,      │ Who sits far from    │
 │                                   │ region?, min_decisions?, min_z           │ their peers?         │
 │ ssa_alj_within_office_variation   │ office?, region?, FY?, min_decisions,    │ How much do judges   │
 │                                   │ min_judges, sort_by                      │ differ in one office?│
 │ ssa_alj_judge_movements           │ from FY, to FY, office?, include_judges  │ Where did judges     │
 │                                   │                                          │ come and go?         │
 │ ssa_alj_data_quality_notes        │ (none)                                   │ What is missing or   │
 │                                   │                                          │ not in the data?     │
 └───────────────────────────────────┴──────────────────────────────────────────┴──────────────────────┘
```

Suggested call flow for an LLM:

```
 ssa_alj_list_reports / ssa_alj_data_quality_notes ──► coverage, valid years, limits
        │
        ├─ BIG PICTURE ► ssa_alj_national_trend ──► ssa_alj_compare_periods
        │                     └► ssa_alj_monthly_pace (current-year pace)
        │
        ├─ OFFICES ─────► ssa_alj_compare_offices ──► ssa_alj_get_office_profile
        │                     ├► ssa_alj_outlier_report (level=office)
        │                     ├► ssa_alj_within_office_variation
        │                     ├► ssa_alj_judge_movements
        │                     └► ssa_alj_office_processing_ranking
        │
        └─ JUDGES ──────► ssa_alj_search_judges ──► ssa_alj_get_judge_profile
                              └► ssa_alj_outlier_report (level=judge)
                 (ambiguous name -> error with `candidates`; pick one and retry)
```

### Request path (one tool call)

```
 client ─► tools/call ─► FastMCP validates args ─► tool fn (async)
                                                    │ asyncio.to_thread
                                                    ▼
                                           services.<fn>  (@handled)
                                                    │  resolve snapshot / name / office
                                                    ▼
                                           db.query(sql, params)   read-only SQLite
                                                    │
                                                    ▼
                                    dict (data + notes) or {"error", "hint", ...}
                                                    │
 client ◄─ structured content ◄─────────────────────┘
```

## 4. Resources, prompts, routes

```
 Resources   ssa-alj://about                 text/markdown  measures, time semantics, caveats
 Prompts     compare_office_outcomes(fiscal_year=2024, region="")
             judge_summary(judge_name)
 Routes      GET /health   -> {"status":"healthy","service":"ssa-alj-mcp"}   (platform probes)
             GET /version  -> {"version":"0.1.0"}
 MCP         POST /mcp     streamable-HTTP endpoint (no auth; public data, hackathon posture)
```

## 5. Data model (SQLite, `db/schema.sql`)

```
 report_snapshot ──< alj_disposition >── alj           (judge identity = published name;
 (one row per published   │      │                       name_key folds case/punctuation)
  report; fiscal_year,   │      └──────► hearing_office
  period end)            └────────────► region
        │
        └──< office_ranking >── hearing_office         (National Ranking reports)

 Views
   v_fy_final_snapshot          latest snapshot per fiscal year   <- what the tools query
   v_alj_disposition            + other_dispositions, allowance_rate, denial_rate
   v_office_summary  v_alj_summary  v_office_ranking  v_latest_disposition_snapshot
```

Key semantics the services enforce:

```
 counts are cumulative fiscal-year-to-date (reset each October)
   FY2024:  Oct-23 ─────────────── Jun-24 ───────── Sep-24
                                      │                │
                                   partial          FINAL  <- used for yearly figures
 never add snapshots of one fiscal year together

 allowance_rate = (fully + partially favorable) / total_decisions
 denial_rate    = total_denials / total_decisions
 other          = total_dispositions - total_decisions   (dismissals etc.; inferred)
```

## 6. Repository layout

```
 .
 ├── src/ssa_alj_mcp/          server package (see section 2)
 ├── tests/                    pytest; synthetic SQLite DB built from db/schema.sql
 ├── db/schema.sql             database schema + views
 ├── data/ssa_alj.sqlite       the database the server reads        (git-ignored)
├── eval/                     deterministic harness + gold Qs + RESULTS.md
├── docs/                     architecture, client setup, Docker smoke, protocol
 ├── Dockerfile  manifest.yaml  server.json
 └── scripts/                  crawl/load ETL + mcp_client_demo
```

## 7. Deployment views

```
 LOCAL (stdio)                              REMOTE (HTTP)
 ┌────────┐  spawn   ┌──────────────┐       ┌────────┐ HTTPS /mcp ┌─────────────────────────┐
 │ Goose  │────────► │ uv run       │       │ Goose /│───────────►│ container (Dockerfile)  │
 │ Cursor │◄──stdin──│ ssa-alj-mcp  │       │ ChatGPT│◄───────────│  PORT -> HTTP transport │
 └────────┘  stdout  │ + local .db  │       └────────┘            │  /app/data/ssa_alj.sqlite│
                     └──────────────┘                             └─────────────────────────┘
                                              (any host that runs the Dockerfile + public HTTPS)
```

## 8. Security posture

- Read-only database access; every query is parameterised; tool arguments are length- and
  pattern-validated; no outbound network calls from the server.
- No authentication on `/mcp` (public data, hackathon scope — see `SECURITY.md`).
- Errors are sanitised payloads (`error` + `hint`), never stack traces.
- Data contains judge names as published by SSA; no claimant data.
