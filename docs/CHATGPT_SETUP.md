# Run the server and connect it to ChatGPT

ChatGPT connects to MCP servers **from OpenAI's cloud**, so it cannot reach `localhost`. You need the
server on a public **HTTPS** URL ending in `/mcp`. Two ways to get one:

| Path | Use it for | Effort |
|---|---|---|
| **A. Local server + tunnel** (ngrok or Cloudflare) | Trying it now, demo, development | ~10 min |
| **B. Deploy a container** (any Docker/HTTPS host, e.g. Render) | A stable URL that stays up | Needs the database shipped with the image (see section 7) |

Steps 1-3 are the same for both. Everything below was verified locally except the ChatGPT screens,
whose labels change; follow the intent if a label differs.

---

## 0. Before you start

- **No LLM key is needed** by this server. ChatGPT uses your own ChatGPT account.
- **ChatGPT plan:** custom MCP connectors ("developer mode") are limited to certain plans and, on
  Business/Enterprise/Edu, may need a workspace admin to enable them. Check your plan if the option is
  missing.
- **Hackathon rules:** the event materials say prototypes should use **public data only** and "will
  not be publicly deployed". This dataset is public SSA data, but a tunnel or Render URL is a public
  endpoint. Keep it temporary and ask `mcp@gsa.gov` if unsure.

## 1. Install and check the database

```bash
cd GSA-Hackathon-SSA-LegalOpenData-MCP-Server
uv sync
ls -lh data/ssa_alj.sqlite        # ~40 MB; if missing, see "Rebuild the database" at the end
uv run pytest -q                  # unit + MCP protocol tests should pass
```

## 2. Start the server in HTTP mode

```bash
MCP_TRANSPORT=streamable-http uv run ssa-alj-mcp
```

It listens on `http://127.0.0.1:8000`. Leave this terminal open. To use another port:
`MCP_PORT=8765 MCP_TRANSPORT=streamable-http uv run ssa-alj-mcp`.

## 3. Check it locally (second terminal)

```bash
curl http://127.0.0.1:8000/health          # {"status":"healthy","service":"ssa-alj-mcp"}
uv run python data/scripts/mcp_client_demo.py --url http://127.0.0.1:8000/mcp
```

The demo should print `tools/list -> 15 tools`, a `tools/call` result and the resource and prompt
calls. If this fails, fix it before going further.

Optional visual check: `npx @modelcontextprotocol/inspector` and connect with transport
*Streamable HTTP* to `http://127.0.0.1:8000/mcp`.

---

## 4. Path A: expose it with a tunnel

Pick one tunnel tool (neither is installed on this machine yet). **No token or account is needed for
the Cloudflare route**; ngrok does need a free account and authtoken. Other no-account options
(untested here): `ssh -R 80:localhost:8000 nokey@localhost.run` or `npx localtunnel --port 8000`.

**Cloudflare quick tunnel (no account, no token), recommended:**

```bash
brew install cloudflared
cloudflared tunnel --url http://127.0.0.1:8000
# prints https://<random-words>.trycloudflare.com
```

**ngrok (free account and authtoken needed):**

```bash
brew install ngrok
ngrok config add-authtoken <your-token>
ngrok http 8000
# prints https://<something>.ngrok-free.app
```

Your MCP URL is the public address plus `/mcp`:

```
https://<your-tunnel-host>/mcp
```

Test it from outside:

```bash
curl https://<your-tunnel-host>/health
uv run python data/scripts/mcp_client_demo.py --url https://<your-tunnel-host>/mcp
```

Notes:

- Use `/mcp` **without a trailing slash** (`/mcp/` answers with a redirect).
- The server accepts any `Host` header, so tunnel hostnames work without extra configuration.
- Free tunnel URLs **change every restart**; update the ChatGPT connector when they do.
- Keep both the server and the tunnel running while you use ChatGPT.

## 5. Add it to ChatGPT

1. Open ChatGPT **Settings** and find **Connectors** (sometimes under *Apps & Connectors*).
2. Under **Advanced**, turn on **Developer mode** (this is what allows custom MCP servers).
3. Choose **Create** / **Add custom connector** and fill in:

   | Field | Value |
   |---|---|
   | Name | `SSA ALJ Open Data` |
   | Description | Public SSA hearing-office and ALJ disposition statistics, FY2010-2026 |
   | MCP server URL | `https://<your-tunnel-host>/mcp` |
   | Authentication | **None** (the server has no auth) |

4. Save. ChatGPT connects and lists the tools. You should see 15 tools (`ssa_alj_*`).
5. In a **new chat**, open the **+** / tools menu, choose **Developer mode** (or the connector name)
   and enable the `SSA ALJ Open Data` connector for that chat.

Reference config in case a client wants JSON (Goose, Claude Code, and similar clients use a block like):

```json
{
  "mcpServers": {
    "ssa-alj": { "url": "https://<your-tunnel-host>/mcp" }
  }
}
```

For a local **stdio** client (no tunnel needed), use the command instead:
`uv --directory <repo path> run ssa-alj-mcp`.

## 6. Try it

Ask ChatGPT, one at a time, and confirm it calls the tools (it shows each tool call):

1. "Using the SSA ALJ tools, what data do you have and what years does it cover?"
2. "How has the national allowance rate for SSA hearings changed since 2010? Which years had the
   fewest judges?"
3. "Which hearing offices had the highest and lowest allowance rates in fiscal year 2024 (at least
   2,000 decisions)?"
4. "Compare the Atlanta North office between FY2019 and FY2024."
5. "Are there data gaps I should know about for fiscal year 2026?"

Good signs: answers quote an *as of* date, mention that counts are fiscal-year-to-date, and carry the
case-mix caveat on outlier or rate comparisons.

### If something goes wrong

| Symptom | Likely cause and fix |
|---|---|
| Can't create a connector / no Developer mode | Plan or workspace admin setting; see section 0. |
| "Unable to connect" / timeout | Server or tunnel not running, wrong URL, or `/mcp/` with a slash. Re-run the `curl .../health` and demo checks against the public URL. |
| Connector worked yesterday, fails today | Free tunnel URL changed. Update the connector URL. |
| Tools list is empty or stale | Remove and re-add the connector, then start a new chat. |
| `{"error": "The SSA ALJ database is not available..."}` | `data/ssa_alj.sqlite` missing on the machine running the server (or `SSA_ALJ_DB_PATH` wrong). |
| ChatGPT answers without calling a tool | Enable the connector for that chat, or say "use the SSA ALJ tools". |
| Browser-side CORS errors | Not expected; ChatGPT calls from OpenAI's servers, not your browser. |

## 7. Path B: a stable URL (container host)

The repo already has a `Dockerfile` (HTTP on `$PORT`, health check `/health`) and
`manifest.yaml` (cloud.gov-style). The one open decision is how the database gets into the
image, because `data/` is git-ignored:

| Option | How |
|---|---|
| Commit a compressed DB | `gzip -k data/ssa_alj.sqlite` (~16 MB) and decompress at container start. |
| Git LFS | Track `data/ssa_alj.sqlite`; the build host must support LFS. |
| Download at start | Host the file as a release asset and fetch it in the container entrypoint. |

Then: build from the Dockerfile on the host, set no secrets, health check path `/health`, and use
`https://<service-host>/mcp` in step 5. Render specifics (service type *Web Service*, runtime
*Docker*) are not yet written or tested here.

## 8. Stop and clean up

- Press `Ctrl+C` in the tunnel terminal and in the server terminal.
- In ChatGPT, delete or disable the connector when you are done.
- A tunnel URL is public while it runs: anyone with the link can call the tools (read-only public
  data). Do not leave it running unattended.

## Optional hardening (not implemented)

If you keep a public URL for long, add a bearer token check in front of `/mcp` (ChatGPT custom
connectors can send an API key or OAuth). Tell me and I will add a `MCP_AUTH_TOKEN` setting.

## Rebuild the database (only if `data/ssa_alj.sqlite` is missing)

```bash
uv run --group etl data/scripts/crawl_ssa_alj.py    # ~7 min, resumable; downloads the 198 SSA XML files
uv run data/scripts/load_ssa_alj.py                 # ~10 s; writes data/ssa_alj.sqlite
```
