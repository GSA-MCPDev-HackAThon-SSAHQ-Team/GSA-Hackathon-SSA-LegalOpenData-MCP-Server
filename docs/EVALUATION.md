# Evaluation guide

How this repo tests the SSA ALJ MCP server for **Criterion 2** (performance & reliability): what each eval is, what inputs it uses, and how to read the outcomes.

**Recorded scores:** [eval/RESULTS.md](../eval/RESULTS.md)  
**Index / commands:** [eval/README.md](../eval/README.md)  
**MCPJam corrected cases:** [eval/mcpjam/ssa-alj-agent-cases.md](../eval/mcpjam/ssa-alj-agent-cases.md)  
**External screenshots:** [eval/screenshots/](../eval/screenshots/) — mcpevals.ai (16/16 tools), MCP Playground (3/3), and [MCPJam](https://app.mcpjam.com/) agent suite ([live suite](https://app.mcpjam.com/p/v97c3xpqc4pncp96erm94b06n18jf6sj/evaluate/suite/md7581a91f0rvddjatv66zd8md8je0qa), Claude / ChatGPT / Cursor clients; Run #1 = 71%). Embedded in [RESULTS.md](../eval/RESULTS.md); failure analysis in [LEARNINGS.md](LEARNINGS.md).

---

## Big picture

| Eval | Needs LLM? | DB | Lives in | Judges see |
|---|---|---|---|---|
| Layer A — deterministic suites | No | Real `data/ssa_alj.sqlite` | `eval/deterministic/` | Exact answers, tool-choice siblings, errors, latency, HTTP health |
| Layer A — scripted multihop | No | Real DB | same runner | Multi-tool path without an agent |
| Layer B — mcpevals SDK | Yes | Real DB via stdio server | `eval/sdk/` (nested uv project) | Agent tool choice + refusal (`Expect.*`) |
| MCPJam agent suite | Yes (host) | Deployed or local `/mcp` | `eval/mcpjam/` (case text + notes) | Tool selection, refusal, regional trends |
| CI unit / MCP protocol | No | Synthetic SQLite | `tests/` | Regression safety net (15 tools, tags, guardrails) |

Reproduce Layer A:

```bash
uv run python eval/deterministic/run_eval.py --http
```

Optional Layer B (`mcpevals`; needs `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`):

```bash
cd eval/sdk && uv sync && uv run pytest -q
```

See [eval/sdk/README.md](../eval/sdk/README.md). Nested project keeps MCP SDK 1.x for `mcp-agent` while the server stays on FastMCP 4 / mcp 2.x.

---

## Layer A — deterministic (`eval/deterministic/`)

One runner (`run_eval.py`) loads cases from `cases.json` and writes `last_run.json`. No model, no network to SSA — only local SQLite (+ optional local HTTP).

### 1. Gold suite (`gold`)

**Purpose:** Prove tool/service outputs match known-correct values for 12 realistic questions.

**Inputs:** Fixed kwargs per case (e.g. `compare_offices(fiscal_year=2024, min_decisions=1000)`).

**Checks:** A JSON path equals an expected value (FY, rate, office name, gap_pts, etc.).

**Natural-language twins:** Same 12 questions live in [`eval/gold/evaluation.xml`](../eval/gold/evaluation.xml) (and [`questions.csv`](../eval/gold/questions.csv)).

| ID | What it verifies (short) |
|---|---|
| G1 | Peak national allowance FY → 2010 |
| G2 | FY2024 national allowance → 0.5842 |
| G3 | Top office FY2024 (≥1000 decisions) → QUEENS |
| G4 | CHARLESTON WV FY23→24 change pts → 11.1 |
| G5 | Miami highest judge FY2024 → Cartledge, James C |
| G6 | Miami within-office gap_pts → 41.7 |
| G7 | National Ranking rank 1 → PONCE |
| G8 | Peak judge headcount FY → 2017 |
| G9 | Dataset is not case-mix adjusted |
| G10 | FY2010 national allowance → 0.6717 |
| G11 | Coverage has 17 fiscal years |
| G12 | FY2024 monthly pace has 12 periods |

### 2. Tool-choice suite (`tool_choice`)

**Purpose:** Catch wrong sibling-tool selection (Criterion 3). Example: processing-speed rank
must use `office_processing_ranking` (PONCE), not `compare_offices` (QUEENS on allowance rate).

### 3. Error suite (`errors`)

**Purpose:** Graceful failure — actionable `error` (and usually `hint`), never a stack trace to the client.

| ID | Bad input | Expect |
|---|---|---|
| E1 | Unknown judge | `error` + `hint` |
| E2 | Unknown office | `error` + `hint` |
| E3 | FY 1999 (no data) | `error` + `hint` |
| E4 | Invalid `as_of` | `error` + `hint` |
| E5 | Invalid `sort_by` | `error` + `hint` |
| E6 | Ambiguous `CHARLESTON` | `error` (candidates) |
| E7 | Outlier `min_decisions` too high | `error` + `hint` |
| E8 | Invalid `group_by` | `error` |

### 4. Shape suite (`shape`)

**Purpose:** Successful payloads stay well-formed for agents (pagination / `notes` / `snapshot` keys).

### 5. Latency suite (`latency`)

**Purpose:** Stable interactive performance on the real DB.

**Method:** Repeat heavier calls (`national_trend`, `compare_periods`, `outlier_report`, `monthly_pace`, `judge_movements`); report p50 / p95 / mean ms.

**Not a load test** — enough to show the server stays snappy for agent loops.

### 6. Scripted multihop (`multihop_scripted_agent`)

**Purpose:** Agent-like path without an LLM: coverage → rank offices → profile QUEENS → outliers → national trend.

**Success:** Each step’s expected fact holds (e.g. top office QUEENS, peak FY 2010).

### 7. HTTP smoke (`--http`)

**Purpose:** Streamable-HTTP transport reliability.

**Method:** Start `ssa-alj-mcp` with `MCP_TRANSPORT=streamable-http`, `GET /health` until `db_ok: true`, sample latency, shut down.

---

## Layer B — mcpevals SDK (`eval/sdk/`)

**Purpose:** Same class of agent checks as MCPJam, but code-defined in pytest via PyPI `mcpevals`
(`Expect.tools.was_called`, content regex). Spawns this repo’s server over stdio.

**Needs:** `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`. Offline smoke tests in that folder run without a key.

**Tests & results (separate MD):** [`eval/sdk/RESULTS.md`](../eval/sdk/RESULTS.md) — not mixed into [`eval/RESULTS.md`](../eval/RESULTS.md).  
Setup: [`eval/sdk/README.md`](../eval/sdk/README.md).

**Not the same as** the hosted [mcpevals.ai](https://mcpevals.ai) screenshots under `eval/screenshots/`.

---

## MCPJam agent suite (`eval/mcpjam/`)

**Purpose:** Measure whether a real MCP host (Claude Desktop, ChatGPT, Cursor) with **only** this
server’s tools can answer analyst questions and refuse forecasts.

| Piece | Role |
|---|---|
| [`ssa-alj-agent-cases.md`](../eval/mcpjam/ssa-alj-agent-cases.md) | Corrected Import-test-cases text (A1–A6, E1–E4 already reflected) |
| Refusal / regional notes | Run #1 traces; see [LEARNINGS.md](LEARNINGS.md) §4–§7 |
| Screenshots | [`eval/screenshots/mcpjam/`](../eval/screenshots/mcpjam/) |

Paste [`ssa-alj-agent-cases.md`](../eval/mcpjam/ssa-alj-agent-cases.md) into the MCPJam suite editor
before re-running. Do not require `ssa_alj_source_links` when snapshot tools already embed
`snapshot.sources`, and do not use “No tool should be called” on the refusal case.

Server-side fixes already in this repo (re-run after deploy): B1/B2 (`scope_note` + instructions),
S1/S2 (`national_trend` year-field series bounds), PII/security guardrails, tool
`meta.category` groups (`discovery` / `lookup` / `analysis`).

---

## CI tests (`tests/`)

**Purpose:** Fast, deterministic regression on a **tiny synthetic** DB (not the full SSA file).

| Area | Examples |
|---|---|
| MCP protocol | All 15 tools registered; `meta.category` tags; validation errors |
| Services | Judge/office happy paths + error payloads |
| Analytics | Trends, outliers, movements |
| Discovery / guardrails | `scope_note`; PII/security refusals |
| Formatting / health | Markdown errors; `/health`-related helpers |

```bash
uv run pytest -q
```

These complement Layer A: CI catches breakage without requiring the 40MB SQLite build; Layer A proves outcomes on the real dataset.

---

## Suggested reading order for judges

1. This page — what each eval means  
2. [eval/RESULTS.md](../eval/RESULTS.md) — dated outcomes  
3. `eval/deterministic/last_run.json` — machine-readable log  
4. [LEARNINGS.md](LEARNINGS.md) — MCPJam Run #1 failures and applied fixes  
5. [eval/mcpjam/ssa-alj-agent-cases.md](../eval/mcpjam/ssa-alj-agent-cases.md) — corrected agent cases  
