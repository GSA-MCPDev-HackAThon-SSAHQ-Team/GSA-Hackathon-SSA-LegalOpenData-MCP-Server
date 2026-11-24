# MCP protocol eras this server supports

FastMCP 4 / current MCP SDKs speak two wire eras. This server supports both.

| | Legacy (≤ ~2025-11-25) | Modern (2026-07-28) |
|---|---|---|
| Handshake | `initialize` + `notifications/initialized` | `server/discover` (stateless) |
| Session | `mcp-session-id`; end with `DELETE /mcp` | No session |
| `ping` | Yes | Not available |
| Tools / resources / prompts | `tools/list`, `tools/call`, `resources/*`, `prompts/*` | Same method names |

Local clients (Claude Desktop, Goose) typically use the **legacy** handshake over stdio.
The FastMCP Python client defaults to the **modern** era (`mode="auto"`); pass `--legacy` to
`data/scripts/mcp_client_demo.py` to force initialize + ping.

See [docs/README.md](README.md) for the method table and demo commands.
