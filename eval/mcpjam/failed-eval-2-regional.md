# Failed Eval 2 — regional allowance trends (F3 / F4)

| | |
|---|---|
| Suite case | Compare allowance rates across hearing offices and identify regional trends |
| Run | `mh7b6pbj` |
| Model | `anthropic/claude-haiku-5.5` · Claude Desktop |
| Iterations | **0/2** passed |
| Screenshots | [`../screenshots/mcpjam/`](../screenshots/mcpjam/) `05`–`10`, `33` |
| Analysis | [`docs/LEARNINGS.md`](../../docs/LEARNINGS.md) §7 |

## Prompt

> Show me the hearing offices with the highest and lowest allowance rates. I want to understand regional variation in how cases are decided.

## What the scorer expected (Run #1 — superseded)

1. `ssa_alj_source_links` (`report_kind=disposition`)
2. `ssa_alj_compare_offices` (`sort_by=allowance_rate`)
3. `ssa_alj_national_trend` (`group_by=region`)
4. Response contains `allowance`

## What the session did (F3)

- Called `compare_offices` (highest + lowest), `data_quality_notes`, and `national_trend` (FY2026 only, no `group_by`)
- Did **not** call `source_links` or `national_trend` with `group_by=region`
- Reply had useful office tables; Selection / Steps failed on missing expected tools (positional Tool Calls diff)

## Fix posture

- **Eval (E1–E4):** **written** in [`ssa-alj-agent-cases.md`](ssa-alj-agent-cases.md) — split into
  `c_office_regional_variation` (`compare_offices` only; `ssa.gov` in reply; **no** mandatory
  `source_links` / `group_by=region`) and `c_regional_trend_decade` (`national_trend` with
  `group_by=region`, omit year args). Paste into MCPJam UI before re-run.
- **Server (S1/S2):** **applied** — `national_trend` year fields describe a series (omit = every
  year on record); docstring points regional-over-time at `group_by=region` and one-year office
  rankings at `compare_offices`. Snapshot tools keep embedding `snapshot.sources`.
