# Architecture — SSA ALJ Open Data MCP Server

This server is a thin, read-only MCP layer over public SSA hearing-office ALJ disposition
data (fiscal years 2010–2026). Clients ask questions; the server answers from a local SQLite
file. It never scrapes SSA at request time and never invents FYTD semantics in the model’s head.

---

## What sits where

```
   data/ssa_alj.sqlite   (~311k disposition rows, FY2010–2026)
            │
            │ opened READ-ONLY (mode=ro, PRAGMA query_only)
            ▼
 ┌────────────────────────────── MCP SERVER (src/ssa_alj_mcp) ─────────────────────────────────┐
 │                                                                                              │
 │   MCP clients                                                                                │
 │   ┌──────────────┐  stdio (local subprocess)      ┌──────────────────────────────────────┐   │
 │   │ Goose        │◄──────────────────────────────►│                                      │   │
 │   │ Claude Code  │                                │   FastMCP app  (app.py)              │   │
 │   │ Claude Desktop│ streamable-HTTP  /mcp         │                                      │   │
 │   │ MCP Inspector│◄──────────────────────────────►│   tools · resources · prompts        │   │
 │   │ ChatGPT      │  (Render / Docker / cloud.gov) │   + /health  /version                │   │
 │   └──────────────┘                                └──────────────────────────────────────┘   │
 └──────────────────────────────────────────────────────────────────────────────────────────────┘
```

`app.py` stays thin: build FastMCP, register pieces, pick a transport.

```
 app.py
  │
  ├── tools/          15 async tools (one file each) → validate args, call a service
  ├── services/       sync query logic (SQL lives here)
  │     reports · judges · offices · trends · analysis · workforce · quality
  │     + common.py / sql.py
  ├── db.py           read-only sqlite3, parameterised queries only
  ├── resources/      ssa-alj://about
  ├── prompts/        compare_office_outcomes, judge_summary
  └── routes.py       GET /health, GET /version (HTTP only)
```

Transport is boring on purpose:

```
 PORT set?              → HTTP on 0.0.0.0:$PORT     (Render, Docker, …)
 MCP_TRANSPORT=http?    → HTTP on MCP_HOST:MCP_PORT (local smoke)
 otherwise              → stdio                     (Goose, Claude Desktop, Inspector)
```

---

## Tools

Every tool is read-only and idempotent. List results share a small envelope
(`total`, `count`, `offset`, `has_more`, `next_offset`, `items`, `notes`). Snapshot-scoped
tools also return `snapshot: {period_end, fiscal_year, report}`. Pass `response_format=markdown`
when you want a short prose summary instead of JSON.

**Lookup**

| Tool | Typical inputs | Answers |
|---|---|---|
| `ssa_alj_list_reports` | fiscal year? | What’s loaded, and what’s the as-of date? |
| `ssa_alj_business_queries` | query?, category? | Curated questions, or a tool plan for custom text |
| `ssa_alj_source_links` | year?, as_of?, kind? | SSA HTML/XML links to verify on ssa.gov |
| `ssa_alj_search_judges` | name, office?, year? | Which published name is this? |
| `ssa_alj_get_judge_profile` | name, year? | One judge by year vs national |
| `ssa_alj_compare_offices` | year / as-of, region?, sort | Highest / lowest offices on a measure |
| `ssa_alj_get_office_profile` | office, year? | One office over time (and its judges) |
| `ssa_alj_office_processing_ranking` | period?, region? | SSA’s National Ranking report |

**Analysis**

| Tool | Typical inputs | Answers |
|---|---|---|
| `ssa_alj_national_trend` | national \| region, year range | How did rates / volume / headcount move since 2010? |
| `ssa_alj_monthly_pace` | year, office?, region? | Speeding up or slowing down inside one FY? |
| `ssa_alj_compare_periods` | office \| region \| judge, two FYs | What changed most between two years? |
| `ssa_alj_outlier_report` | office \| judge, measure, year? | Who sits far from peers? (not case-mix adjusted) |
| `ssa_alj_within_office_variation` | office?, year? | How much do judges differ inside one office? |
| `ssa_alj_judge_movements` | from FY, to FY | Where did judges come and go? |
| `ssa_alj_data_quality_notes` | — | What’s missing or out of scope? |

A sensible agent path looks like this:

```
 list_reports / data_quality_notes   → know coverage and limits
        │
        ├─ big picture → national_trend → compare_periods
        │                    └─ monthly_pace (within the current year)
        │
        ├─ offices → compare_offices → get_office_profile
        │               ├ outlier_report (office)
        │               ├ within_office_variation
        │               ├ judge_movements
        │               └ office_processing_ranking
        │
        └─ judges → search_judges → get_judge_profile
                       └ outlier_report (judge)
            (ambiguous name → error with candidates; pick one and retry)
```

One call, end to end:

```
 client → tools/call → FastMCP validates → tool (async)
                                            │ to_thread
                                            ▼
                                      services.*  (@handled)
                                            │ resolve snapshot / name / office
                                            ▼
                                      db.query(sql, params)
                                            │
 client ← structured content ← dict + notes  (or {error, hint})
```

---

## Resources, prompts, HTTP

| Kind | What |
|---|---|
| Resource | `ssa-alj://about` — measures, time rules, caveats |
| Prompts | `compare_office_outcomes`, `judge_summary` — short playbooks that name which tools to call |
| Routes | `/health`, `/version` for platform probes |
| MCP | `POST /mcp` — streamable HTTP, no auth (public data, hackathon posture) |

---

## Data model

Built from `db/schema.sql`. Judges are matched by published name only (`name_key` folds case and
punctuation). Offices fold to a city-level base so `MIAMI` and `MIAMI OHO` can share a history.

```
 report_snapshot ──< alj_disposition >── alj
        │                 │
        │                 ├── hearing_office
        │                 └── region
        └──< office_ranking >── hearing_office   (National Ranking reports)

 Views worth knowing
   v_fy_final_snapshot     latest snapshot per FY  ← what yearly tools use
   v_alj_disposition       + other_dispositions, allowance_rate, denial_rate
```

The semantics that matter most:

```
 Counts are cumulative fiscal-year-to-date (reset each October).
 Never add snapshots from the same FY together.

 FY2024:  Oct-23 ──────── Jun-24 ──────── Sep-24
                            partial           FINAL  ← yearly figures

 allowance_rate = (fully + partially favorable) / total_decisions
 denial_rate    = total_denials / total_decisions
 other          = dispositions − decisions   (dismissals etc., inferred)
```

---

## Repo layout

```
 src/ssa_alj_mcp/     FastMCP app, tools, services, resources, prompts
 tests/               pytest against a synthetic SQLite DB
 db/schema.sql        schema + views
 data/ssa_alj.sqlite  what the server reads (shipped for Docker/Render)
 data/raw/            crawled SSA XML mirror
 eval/                deterministic harness + gold questions + RESULTS.md
 docs/                this file, client setup, Docker smoke, protocol
 scripts/             crawl + load ETL, mcp_client_demo
 Dockerfile           HTTP image
```

## Deploy

```
 LOCAL (stdio)                              REMOTE (HTTP)
 ┌────────┐  spawn   ┌──────────────┐       ┌────────┐ HTTPS /mcp ┌─────────────────────────┐
 │ Goose  │────────► │ uv run       │       │ Goose /│───────────►│ container (Dockerfile)  │
 │ Claude │◄──stdin──│ ssa-alj-mcp  │       │ ChatGPT│◄───────────│  PORT → HTTP transport  │
 │ Desktop│  stdout  │ + local .db  │       └────────┘            │  /app/data/ssa_alj.sqlite│
 └────────┘          └──────────────┘                             └─────────────────────────┘
```

## Security (short version)

Read-only DB, parameterised SQL, validated args, no outbound network from the server process.
`/mcp` is unauthenticated on purpose for this public-data hackathon — see `SECURITY.md`. Errors
come back as `{error, hint}`, never stack traces. Judge names appear as SSA published them; there
is no claimant data.

---

## How we approached the problem

This is a **Dataset Access Server** problem: help an agent answer real questions from a messy
public collection, without pretending the model can safely scrape and interpret FYTD XML alone.

What we did, in order:

1. Listed the jobs people actually ask (coverage, office ranks, judge history, trends, “is this
   even in the data?”).
2. Named the hazards (cumulative FYTD counts, schema drift, renaming offices, name-only judges,
   two SSA report families that look alike).
3. Drew a hard line: **semantics live in code and views**; the agent only calls tools.
4. Split offline ETL (crawl/load) from the MCP runtime (tools → services → db).
5. Designed tools so each one owns one job, and docstrings say when *not* to use a sibling.
6. Proved it with gold cases, pytest over MCP, and a fixed DB in the deploy image.

```
 Questions people ask
         │
         ▼
    Goal-oriented MCP tools     ← args, notes, errors + hints
         │
         ▼
    Sync services + SQL views   ← FY-final, rates, office folding
         │
         ▼
    SQLite built offline        ← Data.gov / ssa.gov → crawl → load
```

---

## Problems we hit, and what we settled on

### The main one

SSA publishes ALJ dispositions as dozens of cumulative XML snapshots. An LLM cannot safely answer
“how did allowance rates change?” by fetching those files on the fly.

We considered live scraping (CDN pain, wrong FYTD math, non-reproducible answers) and a single
“run SQL” tool (agents invent bad joins). We built **offline ETL → SQLite → goal-oriented tools**
instead: same database locally, in Docker, and on Render; dangerous rules stay in one place.

### The smaller ones

**Time.** Snapshots inside a year stack up; summing them double-counts. Yearly tools use
`v_fy_final_snapshot` / `resolve_snapshot()`. `monthly_pace` is the deliberate exception: it
differences consecutive FYTD files to show within-year speed.

**Identity.** There is no judge ID, and office labels drift (`MIAMI` vs `MIAMI OHO`). We fold
names carefully, and if a query is ambiguous we return an error with candidates rather than
guessing.

**Two rankings.** Allowance-rate ranks and SSA’s “dispositions per day per ALJ” National Ranking
are different reports. They get different tools and tables on purpose — mixing them is a common
agent mistake.

**Rates ≠ performance.** Allowance and denial rates are not case-mix adjusted. We still return
them (they’re useful), but every path can carry notes, `data_quality_notes` exists for gaps and
out-of-scope topics, and prompts remind the model to say the caveat out loud.

**Messy XML.** Field names drift across years. The loader classifies reports from row fields,
keeps anomalies in `load_issue`, and the crawler is resumable with SHA-256 checksums — we don’t
silently drop awkward rows.

**Tool choice.** Too few mega-tools hide intent; too many micro-tools drown the model. We landed
on thirteen goal tools, with `list_reports` / `data_quality_notes` as the orientation pair, plus
cross-links in docstrings and structured `error` + `hint` payloads.

**Local vs remote.** ChatGPT cannot talk stdio to your laptop. One `app.main` path: stdio by
default, HTTP when `PORT` is set, SQLite copied into the image.

---

## Design choices (tools, services, prompts)

These are the decisions we treat as settled for the hackathon baseline.

### Tools

We expose **jobs**, not SQL. A focused set of named tools beats a passthrough query API because
models routinely get FYTD joins and report types wrong.

Each tool is its own small module: validate inputs, `asyncio.to_thread` into a sync service, return
a dict (or markdown). SQL never lives in the tool file, so services stay easy to unit-test.

Shapes are boring on purpose — list envelope, optional `snapshot`, always room for `notes`,
json-or-markdown. Annotations mark everything read-only. When two tools look alike (pace vs trend,
ranking vs allowance, national outlier vs within-office gap), the docstring says which sibling to
prefer. Closed enums (`sort_by`, `entity`, `measure`, …) stop free-text drift. Ambiguous names and
tiny peer groups fail closed with a hint instead of a confident wrong row.

| Tool | Owns this job | Why it’s shaped this way |
|---|---|---|
| `list_reports` | Coverage / as-of | Orient before anything else |
| `business_queries` | Analyst recipes / custom plans | Catalog + keyword match — not a SQL runner |
| `source_links` | Verify on ssa.gov | Uses stored `source_html_url` / `source_xml_url` |
| `search_judges` | Name resolution | Separate from profile so agents must disambiguate |
| `get_judge_profile` | One judge over years | National rate for context — not a scorecard |
| `compare_offices` | Cross-office disposition ranks | If both are set, `as_of` wins over fiscal year |
| `get_office_profile` | One office’s history | City fold merges label variants |
| `office_processing_ranking` | SSA National Ranking | Kept apart from allowance ranks |
| `national_trend` | Multi-year series | FY-final only |
| `monthly_pace` | Intra-year speed | Explicit FYTD differencing |
| `compare_periods` | Movers between two years | Omit `name` to get a ranked list |
| `outlier_report` | Peer z-scores | Case-mix note always travels with the result |
| `within_office_variation` | Spread inside an office | Pass `office` for detail; omit to rank offices by gap |
| `judge_movements` | Who joined / left / moved | Not rate change — that’s `compare_periods` |
| `data_quality_notes` | Gaps and out-of-scope | Call before claiming something is “missing” |

### Services

MCP handlers are async; the query layer is sync on purpose. Services return plain dicts,
`@handled` wraps failures consistently, and helpers for snapshots and rates live in `common.py`
so every ranking agrees on “which report” and how a rate is defined.

We grouped by domain (`reports`, `judges`, `offices`, `trends`, `analysis`, `workforce`,
`quality`) instead of one giant file or a swarm of tiny helpers. Office-name folding stays with
offices; trends and analysis import it. Analytics that are awkward in SQL (z-scores, gaps, pace)
stay in Python.

ETL owns fidelity; the running server only **reads**. Refreshing data means re-running crawl/load,
not teaching the MCP process to download XML.

### Prompts

We kept two prompts — `compare_office_outcomes` and `judge_summary`. Each is a short playbook:
which tools to call, remember the as-of date, say the case-mix / name-matching caveat. They return
instructions, not data. The durable dictionary lives on `ssa-alj://about` so we don’t burn a tool
slot on static prose.

---

## Where this can grow

**Data.** Schedule crawl/load; fail CI if gold cases regress. New SSA report types become a new
table and usually one new tool — still one job per tool.

**Code.** Start from a gold question, then service → thin tool → docstring cross-links. Extend an
existing domain module before inventing a ten-mode mega-tool. Keep pagination and `notes` on every
new list.

**Quality.** Grow `eval/gold`; add an LLM-as-judge pass when keys are available. Feed real
ChatGPT / Claude wrong-tool moments back into docstrings. Add a simple bearer token before leaving
a public URL up for a long time.

**Platform.** Same Dockerfile anywhere `PORT` is injected. The process is mostly stateless
read-only SQLite — replicate the image, or later move to Postgres and keep the SQL close to ANSI.
Cold starts on free hosts are fine for demos.

**Product.** Add prompts only when a workflow keeps going wrong. If you build a UI, call the same
services the tools use. Don’t put claimant-level or non-public data behind this open posture
without revisiting security first.
