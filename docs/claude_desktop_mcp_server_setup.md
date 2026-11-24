# Claude Desktop — connect to the SSA ALJ MCP server (Render)

Use this when Claude Desktop (or claude.ai) should call the **deployed** Render server over
HTTPS. No ngrok, no local `uv` process, and no API keys are required for this MCP server.

**MCP URL (no trailing slash):**

```
https://gsa-hackathon-ssa-legalopendata-mcp.onrender.com/mcp
```

> Remote connectors are reached from **Anthropic’s cloud**, not from your Mac’s network. The
> server must stay publicly reachable on HTTPS port 443 (Render’s default).

For a **local stdio** setup (no Render), see [LOCAL_STDIO_SETUP.md](LOCAL_STDIO_SETUP.md).

---

## 0. Before you start

- Custom / remote MCP connectors need a Claude plan that allows them; org admins may restrict
  custom connectors.
- Free Render apps **spin down when idle**. The first tool call after idle can be slow; retry
  once if the connection test fails.
- Authentication: **None** (public SSA data).

---

## 1. Confirm the server is up

```bash
curl -s https://gsa-hackathon-ssa-legalopendata-mcp.onrender.com/health
# expect: "status":"healthy","db_ok":true
```

If the first request is slow, wait and run it again (cold start).

---

## 2. Add a custom connector (recommended)

Do **not** put the Render URL in `claude_desktop_config.json` for remote MCP. That file is for
**local stdio** servers. Use the Connectors UI instead:

1. Open **Claude Desktop** → **Settings** → **Connectors** (wording may be *Connectors* /
   *Custom connectors*).
2. Choose **Add custom connector** / **Add** → custom / remote MCP.
3. Fill in:

   | Field | Value |
   |---|---|
   | Name | `SSA ALJ Open Data` |
   | Remote MCP server URL | `https://gsa-hackathon-ssa-legalopendata-mcp.onrender.com/mcp` |
   | Authentication / OAuth | **None** / off |

4. Save, then use **Test connection** / **Connect** if offered.
5. Start a **new chat**. Enable the connector for that chat if Claude asks, and **approve**
   tool use when prompted.

You should see **15** tools named `ssa_alj_*`.

The same URL works from **claude.ai** (web) under Connectors if your account allows custom
remote MCP — steps mirror the Desktop UI.

---

## 3. Optional: local stdio instead of Render

Only if you want the server on your machine (no public URL). Edit:

`~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ssa-alj": {
      "command": "/Users/apple/.local/bin/uv",
      "args": [
        "--directory",
        "/Users/apple/Documents/myOpenSource/GSA_MCP_HackAThon/GSA-Hackathon-SSA-LegalOpenData-MCP-Server_Repo/GSA-Hackathon-SSA-LegalOpenData-MCP-Server",
        "run",
        "ssa-alj-mcp"
      ]
    }
  }
}
```

Validate, then **fully quit** Claude Desktop (**Cmd+Q**) and reopen:

```bash
python3 -m json.tool "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

Details and troubleshooting for stdio: [LOCAL_STDIO_SETUP.md](LOCAL_STDIO_SETUP.md).

---

## 4. Try it

Ask one at a time and confirm Claude shows `ssa_alj_*` tool calls:

1. "Using the SSA ALJ tools, what data do you have and what years does it cover?"
2. "How has the national allowance rate for SSA hearings changed since 2010?"
3. "Which hearing offices had the highest and lowest allowance rates in fiscal year 2024 (at least 2,000 decisions)?"
4. "Which offices have the biggest gap between their most and least favourable judges in FY2024?"
5. "What data gaps exist for fiscal year 2026?"

Good answers cite an **as of** date, mention fiscal-year-to-date counts, and note that rates
are not case-mix adjusted.

---

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| Can’t add custom connector | Plan / org policy; try claude.ai Connectors with the same URL. |
| Connection test fails / timeout | Hit `/health` in a browser or `curl` to wake Render; retry. URL must be `/mcp` with **no** trailing slash. |
| Redirect errors | Do not use `/mcp/` — this server and Claude remote connectors are picky about trailing slashes. |
| Tools missing after save | New chat; toggle the connector on; fully quit and reopen Desktop if needed. |
| Claude answers without tools | Say “use the SSA ALJ tools” and confirm the connector is enabled for the chat. |
| Want offline / private use | Use section 3 (stdio) instead of Render. |

---

## 6. Remove it

In **Settings → Connectors**, delete or disable **SSA ALJ Open Data**.  
If you also added a stdio entry, remove `ssa-alj` from `claude_desktop_config.json`, then Cmd+Q and reopen.
