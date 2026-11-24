# Use the server locally over stdio (nothing public)

The client (Goose or Claude Desktop) starts the server as a subprocess on your Mac and talks to it
through stdin/stdout. No port, no tunnel, no token, and no LLM key is needed by the server. The
database file never leaves your machine; only the tool results go to whatever model your client uses.

ChatGPT cannot do this (it only calls remote URLs). See [CHATGPT_SETUP.md](CHATGPT_SETUP.md) for that.

## 1. One-time preparation

```bash
cd /Users/apple/Documents/myOpenSource/GSA_MCP_HackAThon/GSA-Hackathon-SSA-LegalOpenData-MCP-Server_Repo/GSA-Hackathon-SSA-LegalOpenData-MCP-Server
uv sync
ls -lh data/ssa_alj.sqlite      # ~40 MB must exist
uv run pytest -q                # optional: unit + MCP protocol tests
```

Pick **one** of these two launch commands and use it in both clients below. Both were tested here and
completed the MCP handshake and `tools/list` (15 tools).

| Option | Command | Args |
|---|---|---|
| **A. via uv** | `/Users/apple/.local/bin/uv` | `--directory <REPO> run ssa-alj-mcp` |
| **B. venv script** (simplest, no uv at launch) | `<REPO>/.venv/bin/ssa-alj-mcp` | none |

where `<REPO>` is
`/Users/apple/Documents/myOpenSource/GSA_MCP_HackAThon/GSA-Hackathon-SSA-LegalOpenData-MCP-Server_Repo/GSA-Hackathon-SSA-LegalOpenData-MCP-Server`.

**Use absolute paths.** Desktop apps do not inherit your shell `PATH`, so a bare `uv` often fails with
"command not found". Option B avoids that and starts fastest. If you move the repo, update the path.

### Do I have to start the app myself?

**No, not with stdio.** Goose or Claude Desktop launches the server automatically when a chat starts
and stops it when the session ends. Running it by hand in a terminal just sits silently waiting for a
client on stdin (stop with Ctrl+C), so there is nothing to "keep running".

What you do before configuring the client is only: `uv sync`, confirm `data/ssa_alj.sqlite` exists
(above), and optionally `uv run pytest -q`.

Ways to check the server works **without** a chat client:

```bash
# 1. Call every core method through a stdio client (spawns the server itself, prints results)
uv run python data/scripts/mcp_client_demo.py

# 2. Or interactively in a browser UI (Node/npx required)
cd /Users/apple/Documents/myOpenSource/GSA_MCP_HackAThon/GSA-Hackathon-SSA-LegalOpenData-MCP-Server_Repo/GSA-Hackathon-SSA-LegalOpenData-MCP-Server
npx @modelcontextprotocol/inspector .venv/bin/ssa-alj-mcp
```

The Inspector prints a local URL (with a token). Open it, click **Connect**, then **Tools -> List Tools**
(15 tools) and run one, e.g. `ssa_alj_list_reports`.

If you want a server you start by hand and leave running (HTTP mode, also what ChatGPT needs), see
[CHATGPT_SETUP.md](CHATGPT_SETUP.md): `MCP_TRANSPORT=streamable-http uv run ssa-alj-mcp`.

---

## 2. Goose

Goose stores extensions in `~/.config/goose/config.yaml` (already present on this machine). Choose
one way. The server is **not** a Goose built-in, so add it as a command-line (stdio) extension.

### 2a. Goose Desktop (UI)

1. Open Goose, then **Settings -> Extensions** (the extensions list).
2. Click **Add custom extension**.
3. Fill in:

   | Field | Value |
   |---|---|
   | Type | **STDIO** (command-line extension) |
   | Name | `ssa-alj` |
   | Description | `SSA ALJ disposition open data` |
   | Command | Option A: `/Users/apple/.local/bin/uv --directory <REPO> run ssa-alj-mcp` or Option B: `<REPO>/.venv/bin/ssa-alj-mcp` |
   | Timeout | `300` |
   | Environment variables | none needed |

4. Save and make sure the extension toggle is **on**. Start a **new chat**.

### 2b. Goose CLI

```bash
goose configure
# -> Add Extension -> Command-line Extension
# name: ssa-alj
# command: <REPO>/.venv/bin/ssa-alj-mcp        (or the uv command from Option A)
# timeout: 300
# description: SSA ALJ disposition open data
# environment variables: (none)
goose session
```

### 2c. Edit the config file directly

Add this under the existing `extensions:` key of `~/.config/goose/config.yaml` (same shape as the
`knowledgegraphmemory` entry already there):

```yaml
extensions:
  ssa-alj:
    enabled: true
    type: stdio
    name: SSA ALJ Open Data
    description: SSA ALJ disposition open data, FY2010-2026
    cmd: /Users/apple/Documents/myOpenSource/GSA_MCP_HackAThon/GSA-Hackathon-SSA-LegalOpenData-MCP-Server_Repo/GSA-Hackathon-SSA-LegalOpenData-MCP-Server/.venv/bin/ssa-alj-mcp
    args: []
    envs: {}
    env_keys: []
    timeout: 300
    cwd: null
    bundled: null
```

Option A as YAML: set `cmd: /Users/apple/.local/bin/uv` and
`args: [--directory, <REPO>, run, ssa-alj-mcp]`.

Restart Goose (or open a new session). Goose uses whichever model provider you have configured
(`active_provider` in the same file); the server itself needs no key.

---

## 3. Claude Desktop

Config file: `~/Library/Application Support/Claude/claude_desktop_config.json`.
(In the app: **Settings -> Developer -> Edit Config**.)

This machine's file already exists and has **no `mcpServers` key yet**, so add one and keep the other
keys (`coworkUserFilesPath`, `preferences`). Do not replace the whole file.

Prefer Option A for Claude Desktop (macOS often blocks direct execution of scripts under
`Documents/…/.venv/bin/` with `Operation not permitted`):

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

Then **fully quit Claude Desktop (Cmd+Q) and reopen it**; closing the window is not enough. The server
appears under the tools / connectors indicator in a new chat. Approve the tool when asked.

Validate the JSON before restarting: `python3 -m json.tool "$HOME/Library/Application Support/Claude/claude_desktop_config.json"`.

---

## 4. Try it

Ask, one at a time, and confirm it calls the `ssa_alj_*` tools:

1. "Using the SSA ALJ tools, what data do you have and what years does it cover?"
2. "How has the national allowance rate for SSA hearings changed since 2010?"
3. "Which hearing offices had the highest and lowest allowance rates in fiscal year 2024 (at least 2,000 decisions)?"
4. "Which offices have the biggest gap between their most and least favourable judges in FY2024?"
5. "What data gaps exist for fiscal year 2026?"

Good signs: answers quote an *as of* date, say counts are fiscal-year-to-date, and add the case-mix
caveat to rate comparisons.

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| Server fails to start / red status | Run the command from your terminal. Use absolute paths. |
| Claude Desktop: `Operation not permitted` on `.venv/bin/ssa-alj-mcp` | macOS sandbox. Use Option A (`uv` with absolute path) instead of Option B. Grant Claude **Files and Folders** (or Full Disk Access) for Documents in **System Settings → Privacy & Security**. Then Cmd+Q and reopen. |
| `command not found: uv` in the client | Use `/Users/apple/.local/bin/uv` (absolute). |
| Tools missing in Claude Desktop | Quit fully (Cmd+Q) and reopen; check the JSON is valid; look at `~/Library/Logs/Claude/mcp*.log`. |
| Tools missing in Goose | Confirm the extension is enabled and start a new chat; check the timeout is not tiny. |
| `The SSA ALJ database is not available` | `data/ssa_alj.sqlite` missing. Or set `SSA_ALJ_DB_PATH` in the client's env settings. |
| Model does not use the tools | Say "use the SSA ALJ tools", and make sure the extension is enabled for that chat. |
| Changed code, nothing changed | Restart the client; stdio servers start once per session. |

To point at a database elsewhere, add an environment variable in the client:
`SSA_ALJ_DB_PATH=/full/path/to/ssa_alj.sqlite` (Goose: `envs`; Claude Desktop: `"env": {...}`).

## 6. Remove it

- **Goose:** delete or disable the extension in Settings -> Extensions (or remove the `ssa-alj` block).
- **Claude Desktop:** delete the `ssa-alj` entry from `mcpServers`, then quit and reopen.
