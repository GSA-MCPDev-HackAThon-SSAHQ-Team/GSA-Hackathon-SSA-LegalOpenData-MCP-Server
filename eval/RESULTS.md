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

Covers: all 13 tools registered and callable over MCP; pagination envelope; `notes` on success; markdown `response_format`; validation failures as tool errors; missing-DB graceful payload.

Regression: re-run the deterministic suite after code changes; refresh this document from `last_run.json`.
