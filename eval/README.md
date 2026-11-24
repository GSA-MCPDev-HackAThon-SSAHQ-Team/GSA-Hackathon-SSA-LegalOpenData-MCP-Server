# Evaluation

Criterion 2 evidence for the SSA ALJ Open Data MCP server: how we tested, what inputs we
used, and how the server performed.

**Explain each eval:** [docs/EVALUATION.md](../docs/EVALUATION.md)  
**Recorded outcomes (deterministic / external):** [RESULTS.md](RESULTS.md)  
**mcpevals SDK tests & results:** [sdk/RESULTS.md](sdk/RESULTS.md)  
**MCPJam agent cases (corrected):** [mcpjam/ssa-alj-agent-cases.md](mcpjam/ssa-alj-agent-cases.md)  
**External eval screenshots:** [screenshots/](screenshots/) — mcpevals.ai, MCP Playground, and [MCPJam](https://app.mcpjam.com/) (Claude / ChatGPT / Cursor); see [RESULTS.md](RESULTS.md)

## Is an eval SDK used?

**Yes — optional, under [`sdk/`](sdk/):** [LastMile `mcpevals`](https://github.com/lastmile-ai/mcp-eval) drives an LLM against the real stdio server with `Expect.tools` / content assertions.

It is a **nested uv project** (`eval/sdk/`) because `mcp-agent` still requires MCP SDK **1.x**, while this repo’s server uses **FastMCP 4 / mcp 2.x**. Default CI (`uv run pytest` at repo root) does **not** install or run it.

| Layer | How it runs | SDK? |
|---|---|---|
| Deterministic gold / errors / latency | Custom script [`deterministic/run_eval.py`](deterministic/run_eval.py) calling `ssa_alj_mcp.services` (+ optional HTTP `/health`) | No — plain Python |
| CI unit / MCP protocol | [`tests/`](../tests/) via **pytest** + FastMCP in-process client | pytest only (not an agent-eval SDK) |
| **mcpevals agent suite** | [`sdk/`](sdk/) nested project; needs `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` | **Yes — `mcpevals`** |
| MCPJam agent suite | Hosted UI at [app.mcpjam.com](https://app.mcpjam.com/); case text in [`mcpjam/`](mcpjam/) | External product (not a repo dependency) |
| mcpevals.ai / MCP Playground | Browser tool tests vs deployed `/mcp`; screenshots in [`screenshots/`](screenshots/) | External products (name collision with PyPI `mcpevals` — different thing) |

```bash
# Layer A (primary, always runnable, no LLM)
uv run python eval/deterministic/run_eval.py --http

# CI protocol / guardrail regression (no LLM)
uv run pytest -q

# Optional SDK agent eval (nested project + API key)
cd eval/sdk && uv sync && uv run pytest -q
```

## Layers

| Layer | Path | Needs LLM? | Purpose |
|---|---|---|---|
| **A — Deterministic** | [`deterministic/`](deterministic/) | No | Gold answers, error matrix, latency, HTTP `/health`, scripted multi-hop |
| **B — mcpevals SDK** | [`sdk/`](sdk/) | Yes | Agent tool-choice + refusal checks in pytest (`Expect.*`) |
| **Agent cases (MCPJam)** | [`mcpjam/`](mcpjam/) | Yes (host/client) | Corrected suite text for Import test cases; refusal / regional notes |
| Unit / MCP protocol | `tests/` | No | CI safety net (synthetic DB; 15 tools + `meta.category` groups) |

## Gold questions

Source of truth: [`gold/evaluation.xml`](gold/evaluation.xml) (also [`gold/questions.csv`](gold/questions.csv)).
Answers verified against `data/ssa_alj.sqlite`. Deterministic twins live in
[`deterministic/cases.json`](deterministic/cases.json).
