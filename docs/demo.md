# Demo — SSA ALJ Open Data MCP

Short walkthrough for judges and presenters. Full architecture: [ARCHITECTURE.md](ARCHITECTURE.md).  
Judging map: [JUDGE_CRITERIA.md](../JUDGE_CRITERIA.md).

## Live URLs

| What | URL |
|---|---|
| Landing / health | [https://www.ssa-alj-mcpserver-gsahackathon.online/](https://www.ssa-alj-mcpserver-gsahackathon.online/) |
| MCP endpoint | `https://www.ssa-alj-mcpserver-gsahackathon.online/mcp` |

Open the landing page first (tools list, MCP URL). Point ChatGPT / MCPJam / Inspector at `/mcp`.

## Suggested demo flow (~5 minutes)

1. **Problem (30s)** — SSA publishes ALJ disposition XML as many FYTD snapshots (Data.gov `US-GOV-SSA-1199`). Schemas drift; no judge ID; models should not scrape this alone.
2. **Solution (30s)** — Read-only MCP over local SQLite: 15 tools, `ssa-alj://about`, two prompts. Agents call goals (`compare_offices`, `source_links`), not raw XML.
3. **Live check (30s)** — Browser: landing page → copy MCP URL. Optional: `curl https://www.ssa-alj-mcpserver-gsahackathon.online/health`.
4. **Tool calls (2–3 min)** — In any MCP client connected to `/mcp`, run the sample prompts below.
5. **Evidence (1 min)** — Point at [eval/RESULTS.md](../eval/RESULTS.md) (gold + screenshots) and [eval/sdk/RESULTS.md](../eval/sdk/RESULTS.md) (optional SDK). Caveat: rates are not case-mix adjusted / not performance ratings.

## Sample prompts (copy-paste)

**Coverage / discovery**

> What fiscal years of SSA ALJ disposition data does this server cover, and what is the as-of date for FY2024?

**Office comparison (lookup)**

> For fiscal year 2024, which hearing offices have the highest and lowest allowance rates among offices with at least 1000 decisions? Cite the as-of date.

**Verification**

> Give me the official SSA HTML and XML links so I can verify the FY2024 disposition snapshot on ssa.gov.

**Caveat / refusal (guardrails)**

> Which judge will have the best allowance rate next year after adjusting for case mix?

Expect: no invented forecast range; points at quality notes / business queries; reminds that rates are not performance ratings.

## Local demo (optional)

```bash
uv sync
uv run pytest -q
MCP_TRANSPORT=streamable-http uv run ssa-alj-mcp
# another terminal:
curl http://127.0.0.1:8000/health
uv run python data/scripts/mcp_client_demo.py --url http://127.0.0.1:8000/mcp
```

stdio clients: [LOCAL_STDIO_SETUP.md](LOCAL_STDIO_SETUP.md) · ChatGPT remote: [CHATGPT_SETUP.md](CHATGPT_SETUP.md) · Docker: [DOCKER_SMOKE.md](DOCKER_SMOKE.md).

## What to emphasize

- **MCP-shaped tools** (user goals), not thin REST wrappers over each XML file.
- **FYTD semantics** encoded in the server (September = full year; don’t sum snapshots).
- **Verification** via `ssa_alj_source_links` / `snapshot.sources`.
- **Public data only**; read-only SQLite; no claimant PII.
