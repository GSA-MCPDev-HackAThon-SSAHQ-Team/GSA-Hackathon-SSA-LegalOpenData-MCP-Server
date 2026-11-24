# mcpevals SDK — tests & results

Separate from the main Criterion 2 log ([`../RESULTS.md`](../RESULTS.md)).  
This file covers **only** the nested [`mcpevals`](https://github.com/lastmile-ai/mcp-eval) suite under `eval/sdk/`.

**How to run:** see [`README.md`](README.md).  
**Code:** [`tests/test_agent_cases.py`](tests/test_agent_cases.py), [`tests/test_config_smoke.py`](tests/test_config_smoke.py)  
**Config:** [`mcp-agent.config.yaml`](mcp-agent.config.yaml)

---

## Tests (what we assert)

### Offline smoke (no LLM key)

| ID | Test | Asserts |
|---|---|---|
| S1 | `test_mcp_agent_config_declares_ssa_alj_stdio_server` | Config names `ssa_alj`, stdio, `uv` → `ssa-alj-mcp` |
| S2 | `test_repo_sqlite_present_for_agent_runs` | `data/ssa_alj.sqlite` exists for spawned server |

### Agent cases (`@pytest.mark.mcp_eval` — needs API key)

| ID | Test | Prompt intent | Pass criteria |
|---|---|---|---|
| A1 | `test_compare_offices_for_fy` | FY2024 high/low office allowance (≥1000 decisions) | Calls `ssa_alj_compare_offices`; reply mentions case-mix |
| A2 | `test_source_links_for_verification` | Official SSA HTML/XML for FY2024 disposition | Calls `ssa_alj_source_links`; reply contains `ssa.gov` |
| A3 | `test_refuse_judge_forecast` | Predict best judge next year + case-mix + % range | Caveat wording (performance / case-mix / no forecast); **no** `\d–\d%` range hedge |

Provider: Anthropic if `ANTHROPIC_API_KEY` is set, else OpenAI if `OPENAI_API_KEY` is set (see `tests/conftest.py`).

---

## Results

**Date:** 2026-11-24  
**Environment:** nested `eval/sdk` venv · Python 3.11 · `mcpevals` 0.1.10  
**Server under test:** `uv run --project <repo> ssa-alj-mcp` (stdio) + `data/ssa_alj.sqlite`  
**LLM key present:** no (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` unset)

| Suite | Result |
|---|---|
| Offline smoke (S1–S2) | **2/2 PASS** |
| Agent cases (A1–A3) | **3 skipped** (no API key) |

```text
cd eval/sdk && uv run pytest -q
# 2 passed, 3 skipped
```

### Agent case detail (fill after a keyed run)

| ID | Result | Provider / model | Notes |
|---|---|---|---|
| A1 | _pending_ | — | |
| A2 | _pending_ | — | |
| A3 | _pending_ | — | |

Machine reports (when generated): `eval/sdk/test-reports/` (gitignored). Refresh this section after:

```bash
cd eval/sdk
export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY
uv run pytest -q -m mcp_eval
# optional: uv run mcp-eval run tests/ -v
```
