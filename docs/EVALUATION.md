# Evaluation guide

How this repo tests the SSA ALJ MCP server for **Criterion 2** (performance & reliability): what each eval is, what inputs it uses, and how to read the outcomes.

**Recorded scores:** [eval/RESULTS.md](../eval/RESULTS.md)  
**Index / commands:** [eval/README.md](../eval/README.md)

---

## Big picture

| Eval | Needs LLM? | DB | Lives in | Judges see |
|---|---|---|---|---|
| Layer A — deterministic suites | No | Real `data/ssa_alj.sqlite` | `eval/deterministic/` | Exact answers, tool-choice siblings, errors, latency, HTTP health |
| Layer A — scripted multihop | No | Real DB | same runner | Multi-tool path without an agent |
| Layer B — Phoenix agent | Yes | Real DB (via stdio server) | `eval/phoenix/` | LLM tool-use + judge labels |
| CI unit / MCP protocol | No | Synthetic SQLite | `tests/` | Regression safety net |
| Manual client runbook | Optional | Real DB | `eval/manual/` | Goose / Claude / ChatGPT prompts |

Reproduce Layer A:

```bash
uv run python eval/deterministic/run_eval.py --http
```

---

## Layer A — deterministic (`eval/deterministic/`)

One runner (`run_eval.py`) loads cases from `cases.json` and writes `last_run.json`. No model, no network to SSA — only local SQLite (+ optional local HTTP).

### 1. Gold suite (`gold`)

**Purpose:** Prove tool/service outputs match known-correct values for 12 realistic questions.

**Inputs:** Fixed kwargs per case (e.g. `compare_offices(fiscal_year=2024, min_decisions=1000)`).

**Checks:** A JSON path equals an expected value (FY, rate, office name, gap_pts, etc.).

**Natural-language twins:** Same 12 questions live in `eval/phoenix/datasets/ssa-alj-eval-0/evaluation.xml` for Layer B.

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

## Layer B — Phoenix agent (`eval/phoenix/`)

**Purpose:** Measure whether an LLM with **only** this MCP server’s tools can answer the gold questions.

| Piece | Role |
|---|---|
| `datasets/ssa-alj-eval-0/` | 12 Q/A (`evaluation.xml` + CSV) |
| `agent.py` (`SsaAljAgent`) | Launches server over stdio; LangChain + tools |
| `prompts/system_prompt_v1.txt` | Basic analyst conventions |
| `prompts/system_prompt_v2.txt` | + explicit in/out-of-scope rules |
| `judges/correctness_judge.py` | Gold match (`correct` / `incorrect`) |
| `judges/relevance_judge.py` | Scope (`within_scope` / `out_of_scope`) |
| `create_dataset.py` / `run_experiment.py` | Upload dataset + run experiment |

Needs `uv sync --group eval` and USAI keys in `.env` (see `.env.example`). Details: [eval/phoenix/README.md](../eval/phoenix/README.md).

If keys are unavailable, Layer A gold + multihop are the scored evidence; use the manual runbook for interactive demos.

---

## CI tests (`tests/`)

**Purpose:** Fast, deterministic regression on a **tiny synthetic** DB (not the full SSA file).

| Area | Examples |
|---|---|
| MCP protocol | All 13 tools registered; core/analysis calls; validation errors |
| Services | Judge/office happy paths + error payloads |
| Analytics | Trends, outliers, movements |
| Formatting / health | Markdown errors; `/health`-related helpers |

```bash
uv run pytest -q
```

These complement Layer A: CI catches breakage without requiring the 40MB SQLite build; Layer A proves outcomes on the real dataset.

---

## Manual runbook (`eval/manual/`)

Suggested prompts for Goose, Claude Desktop, or ChatGPT — including an out-of-scope “is this judge biased?” probe that should refuse and cite caveats. See [AGENT_RUNBOOK.md](../eval/manual/AGENT_RUNBOOK.md).

---

## Suggested reading order for judges

1. This page — what each eval means  
2. [eval/RESULTS.md](../eval/RESULTS.md) — dated outcomes  
3. `eval/deterministic/last_run.json` — machine-readable log  
4. Optionally Layer B traces in Phoenix after a keyed run  
