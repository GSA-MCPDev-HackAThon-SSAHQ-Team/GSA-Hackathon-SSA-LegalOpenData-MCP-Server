# Judging criteria — how this submission maps

SSA ALJ Open Data MCP Server · GSA MCP Server & SI Agent Government Hackathon  
(Dataset Access Server)

Evidence pointers: [README](README.md) · [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [eval/RESULTS.md](eval/RESULTS.md) · [eval/sdk/RESULTS.md](eval/sdk/RESULTS.md) · [docs/LEARNINGS.md](docs/LEARNINGS.md)

---

## 1. Technical Quality

Whether the server is built to a professional standard — readable, reliable, and designed with the MCP paradigm in mind.

### Criterion 1: Code readability and maintainability

**Official ask:** Logical organization; consistent, self-documenting names; separation of concerns (data models, tool definitions, API/query interactions) so any component can be understood in isolation. Clear file/module structure, meaningful names, comments that explain intent.

**How this project meets it**

- **Layered package:** `tools/` (thin MCP wrappers) → `services/` (SQL/business logic) → `db.py` (read-only SQLite). Models, formatting, and guardrails are separate modules — see [`src/ssa_alj_mcp/README.md`](src/ssa_alj_mcp/README.md) and [`docs/CODEMAP.md`](docs/CODEMAP.md).
- **One tool per file**, shared helpers in `tools/_common.py` (`tool_group`, annotations); services named by domain (`judges`, `offices`, `trends`, …).
- **ETL kept offline** under `data/scripts/` — not mixed into runtime MCP code.
- **Docs for navigability:** architecture diagram, CODEMAP “where to change X”, package README — intent comments where FYTD / case-mix semantics are easy to misuse.

### Criterion 2: Server performance and reliability

**Official ask:** Include evaluation setup and results — how tested, what inputs, how the server performed. Thoughtful design, accurate well-formed responses, graceful errors, stable performance across cases.

**How this project meets it**

| Layer | Where | Outcome (see linked RESULTS) |
|---|---|---|
| Deterministic gold / errors / latency / HTTP | [`eval/deterministic/`](eval/deterministic/) → [`eval/RESULTS.md`](eval/RESULTS.md) | 12/12 gold, 8/8 errors, latency p50s in tens of ms, `/health` ok |
| CI unit + MCP protocol | [`tests/`](tests/) | Synthetic DB; 15 tools, validation, markdown, guardrails |
| External hosts | Screenshots in [`eval/screenshots/`](eval/screenshots/) | mcpevals.ai 16/16 tools; MCP Playground 3/3; MCPJam agent suite (Claude / ChatGPT / Cursor) |
| Optional agent SDK | [`eval/sdk/`](eval/sdk/) → [`eval/sdk/RESULTS.md`](eval/sdk/RESULTS.md) | `mcpevals` pytest `Expect.*` cases (separate log) |

- Responses use pagination envelopes, `notes`, and `snapshot` metadata; bad input returns `{error, hint}` (no stack traces to clients).
- Read-only DB (`mode=ro`), parameterised SQL, no outbound network from the server process.
- Failure analysis and rubric fixes documented in [`docs/LEARNINGS.md`](docs/LEARNINGS.md) and [`docs/EVALUATION.md`](docs/EVALUATION.md).

### Criterion 3: Adherence to MCP design principles

**Official ask:** Built for agents — Pydantic-validated inputs; precise tool names/descriptions for LLM selection; tools around meaningful user goals, not thin REST wrappers.

**How this project meets it**

- **Goal-shaped tools**, not “GET this XML file”: e.g. compare offices, judge profile vs national, within-office variation, source links for verification, curated `business_queries` recipes.
- **Pydantic / Field descriptions** in [`models.py`](src/ssa_alj_mcp/models.py) and per-tool modules; read-only / idempotent annotations; `response_format` json|markdown.
- **Agent-facing surface:** resource `ssa-alj://about`, prompts (`compare_office_outcomes`, `judge_summary`), tool groups `discovery` / `lookup` / `analysis` via tags + `meta.category`.
- **Guardrails** refuse PII/security probes and scope-note forecast / “best performer” asks — so the agent stays inside what the public dataset can support.

---

## 2. Innovation

**Official ask:** Novelty and creativity; creative use of MCP tooling and unique agent workflows.

**How this project meets it**

- Turns a messy multi-year FYTD XML corpus (schema drift, office renames, no judge IDs) into a **stable agent API** with FYTD semantics encoded in services — not left for the model to invent.
- **Verification loop:** `ssa_alj_source_links` + embedded `snapshot.sources` so agents can send humans back to ssa.gov.
- **Multi-client evidence:** same server exercised via Goose/Claude Desktop (stdio), ChatGPT/Render (HTTP), MCPJam multi-model suite, plus optional in-repo `mcpevals` agent harness.
- **Curated business-query catalog** + analysis tools (outliers, movements, monthly pace) that go beyond single-table lookups.

---

## 3. Mission alignment

**Official ask:** Supports mission needs; improves service delivery and oversight.

**How this project meets it**

- Surfaces **public SSA OHO ALJ disposition statistics** (Data.gov `US-GOV-SSA-1199`) for oversight-style questions: office/region trends, processing rankings, workforce moves — without exposing claimant PII.
- Helps analysts and oversight users get **cited, as-of-dated figures** instead of scraping or trusting unverified model counts.
- Explicit caveats (not case-mix adjusted; not a performance rating; no forecasting) reduce misuse in service-delivery or personnel judgments.
- Deployable read-only HTTP endpoint + `/health` supports shared government client setups without a custom ETL per team.

---

## Presentation

**Official ask:** Clear storytelling and explanation; effective demo flow; evidence of testing.

**How this project meets it**

- **Story:** Problem (unusable FYTD XML) → Solution (read-only MCP translation layer) → Tools table and run instructions in the [README](README.md).
- **Demo path:** stdio local clients → streamable-HTTP `/mcp` → Inspector / `mcp_client_demo.py` → Docker/Render; setup docs under [`docs/`](docs/).
- **Evidence pack:** [`eval/RESULTS.md`](eval/RESULTS.md), [`eval/sdk/RESULTS.md`](eval/sdk/RESULTS.md), screenshot gallery, gold questions in [`eval/gold/`](eval/gold/), architecture and data-prep diagrams in [`docs/`](docs/).
