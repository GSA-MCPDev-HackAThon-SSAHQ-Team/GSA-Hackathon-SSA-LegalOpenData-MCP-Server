# Evaluation

Criterion 2 evidence for the SSA ALJ Open Data MCP server: how we tested, what inputs we
used, and how the server performed.

**Explain each eval:** [docs/EVALUATION.md](../docs/EVALUATION.md)  
**Recorded outcomes:** [RESULTS.md](RESULTS.md)

## Layers

| Layer | Path | Needs LLM? | Purpose |
|---|---|---|---|
| **A — Deterministic** | [`deterministic/`](deterministic/) | No | Gold answers, error matrix, latency, HTTP `/health`, scripted multi-hop |
| **B — Agent + judges** | [`phoenix/`](phoenix/) | Yes (USAI gateway) | LLM uses tools only; Phoenix correctness + scope judges |
| Unit / MCP protocol | `tests/` | No | CI safety net (synthetic DB) |

```bash
# Layer A (primary, always runnable)
uv run python eval/deterministic/run_eval.py --http

# Layer B (optional, needs .env + Phoenix)
uv sync --group eval
cd eval/phoenix && uv run create_dataset.py --dataset-name ssa-alj-eval-0 --dry-run
```

## Gold questions

Source of truth: [`phoenix/datasets/ssa-alj-eval-0/evaluation.xml`](phoenix/datasets/ssa-alj-eval-0/evaluation.xml)
(also as CSV for Phoenix). Answers verified against `data/ssa_alj.sqlite`.
