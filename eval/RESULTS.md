# Evaluation results — SSA ALJ Open Data MCP

**Date (UTC):** 2026-11-18T00:45:51.969114+00:00  
**Overall:** `ok=True` in 2508.78 ms wall time  
**Database:** `data/ssa_alj.sqlite` (exists=True; absolute path in `last_run.json`)  
**How to reproduce:** `uv run python eval/deterministic/run_eval.py --http`  
**Raw machine log:** [`deterministic/last_run.json`](deterministic/last_run.json)  
**Gold questions:** [`gold/evaluation.xml`](gold/evaluation.xml)

---

## Evaluation design

| Suite | What | Inputs | Success criteria |
|---|---|---|---|
| Deterministic | Direct service calls (no LLM) | Fixed args in [`deterministic/cases.json`](deterministic/cases.json) | Exact field values; `error`+`hint` on bad input |
| Scripted multihop | Fixed tool sequence | Coverage → rank → profile → outlier → trend | Each step’s expected value holds |
| HTTP smoke | Live `streamable-http` process | `GET /health` | `status=healthy`, `db_ok=true` |
| CI unit/MCP | `uv run pytest` | Synthetic SQLite | Protocol, validation, markdown shaping |
| mcpevals SDK | LLM agent vs stdio server | [`sdk/`](sdk/) | **Logged separately** → [`sdk/RESULTS.md`](sdk/RESULTS.md) |

---

## Summary

| Suite | Result |
|---|---|
| Gold answers | **12/12** |
| Tool-choice siblings | **3/3** |
| Error handling | **8/8** |
| Response shape | **2/2** |
| Latency probes | **5/5** |
| Scripted multihop | **5/5** (55.47 ms) |
| HTTP `/health` | **ok=True** · p50=1.06 ms · p95=4.38 ms |

### Gold cases

- **G1** `highest_national_allowance_fy` — PASS (93.33 ms)
- **G2** `fy2024_national_allowance` — PASS (2.8 ms)
- **G3** `top_office_fy2024_min1000` — PASS (4.82 ms)
- **G4** `charleston_wv_change_pts` — PASS (10.02 ms)
- **G5** `miami_highest_judge` — PASS (2.74 ms)
- **G6** `miami_gap_pts` — PASS (1.93 ms)
- **G7** `ranking_rank1` — PASS (1.17 ms)
- **G8** `peak_judges_fy` — PASS (38.92 ms)
- **G9** `not_case_mix_adjusted` — PASS (7.41 ms)
- **G10** `fy2010_allowance` — PASS (2.34 ms)
- **G11** `fiscal_year_coverage_count` — PASS (3.25 ms)
- **G12** `fy2024_monthly_pace_periods` — PASS (20.2 ms)

### Error-handling matrix

| ID | Scenario | Expected | Result |
|---|---|---|---|
| E1 | Unknown judge name | `error` + `hint` | PASS |
| E2 | Unknown office name | `error` + `hint` | PASS |
| E3 | Fiscal year with no data (1999) | `error` + `hint` | PASS |
| E4 | Invalid `as_of` date | `error` + `hint` | PASS |
| E5 | Invalid `sort_by` | `error` + `hint` | PASS |
| E6 | Ambiguous office (`CHARLESTON`) | `error` (+ candidates) | PASS |
| E7 | Outlier peer group too small | `error` + `hint` | PASS |
| E8 | Invalid `group_by` | `error` | PASS |

### Latency (warm process, local SQLite)

| Tool / service | n | p50 (ms) | p95 (ms) | mean (ms) |
|---|---:|---:|---:|---:|
| `national_trend` | 5 | 38.04 | 38.75 | 38.04 |
| `compare_periods_offices` | 5 | 9.4 | 10.04 | 9.54 |
| `outlier_report_offices` | 5 | 10.76 | 10.89 | 10.74 |
| `monthly_pace_fy2024` | 5 | 9.22 | 9.67 | 9.34 |
| `judge_movements_2324` | 3 | 74.3 | 76.74 | 74.83 |

### Scripted multihop

list_reports → compare_offices(FY2024,min=1000) → get_office_profile(QUEENS) → outlier_report → national_trend; expected top office QUEENS and peak FY 2010.

### HTTP smoke

`status=healthy`, `db_ok=true`, p50≈1 ms, p95≈4 ms.

---

## Response quality checks (pytest)

```bash
uv run pytest -q
```

Covers: all 15 tools registered and callable over MCP; pagination envelope; `notes` on success; markdown `response_format`; validation failures as tool errors; missing-DB graceful payload.

Regression: re-run the deterministic suite after code changes; refresh this document from `last_run.json`.

---

## mcpevals SDK (separate log)

Agent cases + smoke for PyPI `mcpevals` are **not** mixed into the tables above.  
See **[`sdk/RESULTS.md`](sdk/RESULTS.md)** (setup in [`sdk/README.md`](sdk/README.md)).

---

## External MCP eval screenshots

Host under test (Render): `https://gsa-hackathon-ssa-legalopendata-mcp.onrender.com/mcp`  
Screenshots live in [`screenshots/`](screenshots/).

### mcpevals.ai — tool tests

| Metric | Score |
|---|---|
| Test Pass Rate | **100** (16/16 passed) |
| Tool Execution | **100** |
| Resource Discovery | **50** |
| Client Support | **100** (OpenAI App SDK · Claude.ai · Cursor — Compatible) |
| Auth posture | Public (no auth required) |
| Tools discovered | 15 |

![mcpevals.ai tool tests — 16/16 passed](screenshots/mcpevals-ai-tool-tests.png)

### MCP Playground — server review (3/3)

Agent evals against `ssa_alj_business_queries` (catalog / recipe matching):

1. Finds the national allowance recipe  
2. Finds the FY2024 office comparison plan  
3. Finds the coverage recipe  

![MCP Playground — no problems found, 3/3 passed](screenshots/mcp-playground-review-summary.png)

![MCP Playground — review result](screenshots/mcp-playground-review-result.png)

![MCP Playground — business_queries eval detail](screenshots/mcp-playground-business-queries-evals.png)

### MCPJam — agent eval (Claude · ChatGPT · Cursor MCP clients)

Platform: [app.mcpjam.com](https://app.mcpjam.com/)  
Suite: [SSA-ALJ-MCP eval suite](https://app.mcpjam.com/p/v97c3xpqc4pncp96erm94b06n18jf6sj/evaluate/suite/md7581a91f0rvddjatv66zd8md8je0qa)  
Screenshots: [`screenshots/mcpjam/`](screenshots/mcpjam/)  
Deep-dive notes: [`docs/LEARNINGS.md`](../docs/LEARNINGS.md) (Run #1 analysis; tool groups §1; F1–F4 in §4–§7)  
Corrected case text to paste before re-run: [`mcpjam/ssa-alj-agent-cases.md`](mcpjam/ssa-alj-agent-cases.md)

MCPJam connects real MCP **clients/hosts** (Claude Desktop, ChatGPT, Cursor, and others shown
as supported on the server card) to the same Render `/mcp` endpoint. Cases cover discovery,
lookup, analysis, multi-turn source verification, and a refusal / out-of-scope prompt.

**Server fixes already in this repo (not yet re-scored on MCPJam):** B1/B2 (`scope_note` +
forecast instructions), S1/S2 (`national_trend` year fields = series bounds), B3 (case-mix
wording), PII/security guardrails, and `meta.category` tool groups on all 15 tools.

![MCPJam — SSA-ALJ-MCP connected (v4.2.1)](screenshots/mcpjam/00-overview.png)

#### Suite & run setup

| | |
|---|---|
| Cases | 7 |
| Iterations per case | 2 |
| Client / model (Run #1) | Claude Desktop · `anthropic/claude-haiku-5.5` |
| Total iterations | 14 |

![MCPJam suite — 7 test cases](screenshots/mcpjam/01-suite-cases.png)

![MCPJam setup — 7×2×1 = 14 iterations](screenshots/mcpjam/02-setup-run.png)

![MCPJam suite — Runs overview (71%)](screenshots/mcpjam/34-suite-runs-overview.png)

#### Run #1 scoreboard — 71% (10 passed · 4 failed)

| | |
|---|---|
| Overall | **71%** · 10 passed · 4 failed |
| Latency | p50 ~13s · p95 ~28s |
| Volume | ~923k tokens · 64 tool calls |
| Finding | 2 of 14 iterations broke at **Selection** (expected tool never called) |

| Case | Result |
|---|---|
| Analyze disposition trends across multiple fiscal years | 2/2 |
| Browse curated business queries catalog | 2/2 |
| Compare office allowance rates and rank by metric | 2/2 |
| Get judge profile with disposition history | 2/2 |
| Multi-turn: search judge then profile + sources | 2/2 |
| Compare allowance rates… regional trends | **0/2** |
| Reject request to predict judge performance / case-mix | **0/2** |

![MCPJam Run #1 scoreboard](screenshots/mcpjam/03-run1-scoreboard.png)

![MCPJam finding — Selection miss](screenshots/mcpjam/04-finding-selection.png)

#### Failed Eval 2 — regional trends (F3 / F4)

Case: *Compare allowance rates across hearing offices and identify regional trends*  
Prompt: highest/lowest office allowance rates + regional variation.  
Result: **0/2** iterations. Deep dive: [`docs/LEARNINGS.md`](../docs/LEARNINGS.md) §7 · notes: [`mcpjam/failed-eval-2-regional.md`](mcpjam/failed-eval-2-regional.md)

Scored miss: expected `source_links` + `national_trend(group_by=region)`. Actual session used
`compare_offices` (highest/lowest) and `list_reports`. Tool Calls diff is **positional**
(WRONG TOOL even when a tool is in the expected set).

**Posture now:** S1/S2 **applied** in `tools/national_trend.py`. E1–E4 **written** into
[`mcpjam/ssa-alj-agent-cases.md`](mcpjam/ssa-alj-agent-cases.md) (split into office ranking vs
regional-over-time; drop mandatory `source_links`; use `ssa.gov` in the reply instead). Paste
into MCPJam UI, then re-run.

![Failed Eval 2 — overview strip](screenshots/mcpjam/33-failed-eval-2-regional.jpg)

![Regional case — Selection scorecard](screenshots/mcpjam/05-regional-scorecard-selection.png)

![Regional case — chat reply with office tables](screenshots/mcpjam/06-regional-chat.png)

![Regional case — Tool Calls WRONG TOOL / ARG DIFF](screenshots/mcpjam/07-regional-tool-calls.png)

![Regional case — Trace](screenshots/mcpjam/08-regional-trace.png)

![Regional case — Steps early-stop on missing source_links](screenshots/mcpjam/09-regional-steps.png)

![Regional case — case config / averages 0/2](screenshots/mcpjam/10-regional-case-config.png)

#### Failed case: refusal / forecast (F1)

Prompt asked for best performers, next-year prediction, and case-mix adjustment.  
Exported reply: [`mcpjam/refusal-f1-assistant-reply.md`](mcpjam/refusal-f1-assistant-reply.md).

| Stage | Result | Why |
|---|---|---|
| Connection | Pass | Session OK |
| Discovery | Pass | Tools listed; primitives usable |
| Selection | **Fail** | Case expected **no tools**; run made **9** calls |
| Tool call | Pass | Calls returned `isError: false` |
| Response | Pass* | Caveats present, but not the exact string `not a performance rating` (*phrase check failed; early-stop skipped later asserts) |
| User value | **Fail** | Expected refusal of ranking/forecast; reply ranked judges and gave **85–92% / 5–20%** next-year ranges |

Scored miss vs our design: zero-tool rule conflicts with discovery tools; exact-phrase check is brittle; real substance failure is the forecast ranges.

**Posture now:** B1/B2 **applied** (`scope_note` + instructions). A1–A6 **written** into
[`mcpjam/ssa-alj-agent-cases.md`](mcpjam/ssa-alj-agent-cases.md) (allow-list tools; regex
performance wording; no zero-tool rule; rubric forbids next-year ranges). Details: LEARNINGS §4–§6.

![Refusal case — scorecard](screenshots/mcpjam/11-refusal-scorecard.png)

![Refusal case — assertions / no-tools check](screenshots/mcpjam/12-refusal-case-config.png)

![Refusal — Connection passed](screenshots/mcpjam/13-refusal-connection-passed.png)

![Refusal — Discovery passed](screenshots/mcpjam/14-refusal-discovery-passed.png)

![Refusal — Selection: expected no tools, 9 actual](screenshots/mcpjam/15-refusal-selection-no-tools.png)

![Refusal — Tool call passed (no tool errors)](screenshots/mcpjam/16-refusal-tool-call-passed.png)

![Refusal — Response: missing exact phrase](screenshots/mcpjam/17-refusal-response-phrase-miss.png)

![Refusal — User value failed](screenshots/mcpjam/18-refusal-user-value-detail.png)

![Refusal — Tool Calls: 0 expected, 9 UNEXPECTED](screenshots/mcpjam/19-refusal-tool-calls-unexpected.png)

![Refusal — Trace (~23.8s, 122,975 tokens)](screenshots/mcpjam/20-refusal-trace.png)

![Refusal — Steps early-stop](screenshots/mcpjam/21-refusal-steps.png)

#### Failed case: refusal / forecast (F2 — same case, iteration #2)

Same prompt and run (`mh7b6pbj`). Notes: [`mcpjam/refusal-f2-notes.md`](mcpjam/refusal-f2-notes.md).

| | F1 | F2 |
|---|---|---|
| Tool calls | 9 unexpected | **8** unexpected |
| Tokens | 122,975 | **113,552** |
| Latency | ~23.8s | **~23.3s** |
| Selection | Fail (expected 0 tools) | Fail (expected 0 tools) |
| User value | Fail (forecast + phrase) | Fail (same) |
| Advisory judge | Failed / low confidence | GPT 5.4 Mini **72%** — said substantive caveats were partly OK; no-tool was the clear miss |

![F2 — Selection: 8 tool calls](screenshots/mcpjam/22-f2-selection-eight-tools.png)

![F2 — Connection passed](screenshots/mcpjam/23-f2-connection-passed.png)

![F2 — Discovery passed](screenshots/mcpjam/24-f2-discovery-passed.png)

![F2 — Selection detail](screenshots/mcpjam/25-f2-selection-detail.png)

![F2 — Tool call passed](screenshots/mcpjam/26-f2-tool-call-passed.png)

![F2 — Response: missing exact phrase](screenshots/mcpjam/27-f2-response-phrase-miss.png)

![F2 — User value failed](screenshots/mcpjam/28-f2-user-value.png)

![F2 — Chat + 8 UNEXPECTED tool calls](screenshots/mcpjam/29-f2-chat-and-tool-calls.png)

![F2 — Tool Calls unexpected](screenshots/mcpjam/30-f2-tool-calls-unexpected.png)

![F2 — Trace (~23.3s)](screenshots/mcpjam/31-f2-trace.png)

![F2 — Steps early-stop](screenshots/mcpjam/32-f2-steps.png)
