# ChatGPT — connect to the SSA ALJ MCP server (Render)

Connect ChatGPT to the deployed MCP server. ChatGPT needs a public HTTPS URL (not
`localhost`). No ngrok, no API keys, no auth token.

**MCP URL (copy exactly — no trailing slash):**

```
https://gsa-hackathon-ssa-legalopendata-mcp.onrender.com/mcp
```

---

## Guiding steps (do these in order)

### Step 1 — Wake the server

Free Render apps sleep when idle. Open a browser or terminal and hit health first:

```bash
curl -s https://gsa-hackathon-ssa-legalopendata-mcp.onrender.com/health
```

Wait until you see something like `"status":"healthy","db_ok":true`.  
If it hangs or fails once, wait ~30–60 seconds and run the same command again.

Optional deeper check from this repo:

```bash
uv run python data/scripts/mcp_client_demo.py --url https://gsa-hackathon-ssa-legalopendata-mcp.onrender.com/mcp
```

### Step 2 — Open ChatGPT connector settings

1. Go to [ChatGPT](https://chatgpt.com) and sign in.
2. Open **Settings** (profile / gear).
3. Open **Connectors** (may appear under **Apps & Connectors**).

### Step 3 — Turn on Developer mode

1. In Connectors / Advanced settings, find **Developer mode**.
2. Turn **Developer mode** **ON**.  
   Without this, you cannot add a custom MCP server.
3. If you do not see Developer mode: your plan or workspace admin may block it — ask an admin or use a plan that allows custom connectors.

### Step 4 — Create the custom connector

1. Click **Create** / **Add custom connector**.
2. Fill in these fields exactly:

   | Field | What to enter |
   |---|---|
   | **Name** | `SSA ALJ Open Data` |
   | **Description** | `Public SSA hearing-office and ALJ disposition statistics, FY2010–2026` |
   | **MCP server URL** | `https://gsa-hackathon-ssa-legalopendata-mcp.onrender.com/mcp` |
   | **Authentication** | **None** |

3. Click **Save** / **Create**.
4. Confirm ChatGPT shows about **15** tools whose names start with `ssa_alj_`.

### Step 5 — Install the plugin and use it in a chat

ChatGPT no longer always shows a per-chat “turn on connector” switch. After you create
the custom MCP server, treat it like a **plugin**:

1. Go to **Settings → Plugins** (or [chatgpt.com/plugins](https://chatgpt.com/plugins)).
2. Find **SSA ALJ Open Data** and click **Install** / **Enable** if it is not installed yet.
3. Start a **new chat**.
4. In the message box, type **`@`**.
5. From the picker, select **SSA ALJ Open Data** (your custom MCP plugin).
6. Then type your question (examples in Step 6) and send.

If `@` does not list it: confirm it is **Installed** under Plugins, refresh the page, and
try a brand-new chat. You can also say explicitly:  
`Use only the SSA ALJ Open Data app / tools for this question.`

### Step 6 — Ask a question that uses the tools

Paste one of these and send. Watch for a visible **tool call** (not a generic guess):

1. `Using the SSA ALJ tools, what data do you have and what years does it cover?`
2. `How has the national allowance rate for SSA hearings changed since 2010?`
3. `Which hearing offices had the highest and lowest allowance rates in fiscal year 2024 (at least 2,000 decisions)?`
4. `Compare the Atlanta North office between FY2019 and FY2024.`
5. `Are there data gaps I should know about for fiscal year 2026?`

**Good answer signs:** cites an “as of” date, says counts are fiscal-year-to-date, notes rates are not case-mix adjusted.

### Step 7 — If something fails, fix then retry

| What you see | What to do |
|---|---|
| Timeout / unable to connect | Repeat **Step 1** to wake Render, then retry the connector. URL must end in `/mcp` with **no** trailing `/`. |
| No Developer mode | Plan/admin — see **Step 3**. |
| Connector saves but no tools | Remove the connector, redo **Step 4**, then a **new** chat (**Step 5**). |
| Answers with no tool calls | Connector not enabled for that chat — redo **Step 5**; say “use the SSA ALJ tools”. |
| Database not available | Render deploy issue — check Render logs / redeploy `main`. |

### Step 8 — Remove later (optional)

**Settings → Connectors** → delete or disable **SSA ALJ Open Data**.

---

## Quick reference

```text
Health:  https://gsa-hackathon-ssa-legalopendata-mcp.onrender.com/health
MCP:     https://gsa-hackathon-ssa-legalopendata-mcp.onrender.com/mcp
Auth:    none
Tools:   15 × ssa_alj_*
```
