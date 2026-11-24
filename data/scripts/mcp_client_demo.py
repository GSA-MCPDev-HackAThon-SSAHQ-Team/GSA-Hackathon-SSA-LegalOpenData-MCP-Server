"""Call every core MCP method against this server and print what comes back.

Each step prints the JSON-RPC method it corresponds to, so it doubles as a protocol walkthrough.

The server speaks two protocol eras, and the demo can show both:
  legacy  (2025-06-18 and earlier): `initialize` handshake + `notifications/initialized`, `ping`,
          session id header.
  modern  (2026-07-28): no handshake or session; `server/discover` instead, every request carries
          protocol version + client capabilities in `params._meta`, and `ping` does not exist.
The FastMCP client picks the modern era automatically when the server supports it.

Usage:
  uv run python data/scripts/mcp_client_demo.py                       # spawns the server over stdio
  uv run python data/scripts/mcp_client_demo.py --legacy              # force the initialize handshake
  uv run python data/scripts/mcp_client_demo.py --url http://127.0.0.1:8000/mcp   # remote / HTTP server
  uv run python data/scripts/mcp_client_demo.py --raw --url http://127.0.0.1:8000/mcp            # raw, legacy
  uv run python data/scripts/mcp_client_demo.py --raw --modern --url http://127.0.0.1:8000/mcp   # raw, modern

Start an HTTP server first with:  MCP_TRANSPORT=streamable-http uv run ssa-alj-mcp
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from mcp.shared.exceptions import MCPError

ROOT = Path(__file__).resolve().parents[2]


def show(method: str, summary: Any) -> None:
    text = summary if isinstance(summary, str) else json.dumps(summary, default=str)
    print(f"{method:28} -> {text[:140]}")


# --------------------------------------------------------------------------- SDK client


async def run_sdk(url: str | None, legacy: bool) -> None:
    transport: Any = url if url else StdioTransport("uv", ["run", "ssa-alj-mcp"], cwd=str(ROOT))
    # Entering `async with` connects and performs the MCP handshake (capability negotiation).
    async with Client(transport, mode="legacy" if legacy else "auto") as client:
        caps = client.server_capabilities
        show(
            "initialize" if legacy else "server/discover",
            {
                "protocol": client.protocol_version,
                "server": client.server_info.name,
                "capabilities": sorted(
                    k
                    for k in ("tools", "resources", "prompts", "logging")
                    if getattr(caps, k, None)
                ),
            },
        )
        try:
            await client.ping()
            show("ping", "ok")
        except MCPError as exc:  # modern era has no ping method
            show("ping", f"not available in this protocol era ({exc.message})")

        tools = await client.list_tools()
        show("tools/list", f"{len(tools)} tools: " + ", ".join(t.name for t in tools[:4]) + ", ...")

        result = await client.call_tool("ssa_alj_list_reports", {})
        cov = result.structured_content["coverage"]
        show(
            "tools/call",
            f"ssa_alj_list_reports -> FY {cov['fiscal_years'][0]}-{cov['fiscal_years'][-1]}",
        )
        result = await client.call_tool(
            "ssa_alj_compare_offices",
            {"fiscal_year": 2024, "min_decisions": 2000, "limit": 1},
        )
        top = result.structured_content["items"][0]
        show("tools/call", f"ssa_alj_compare_offices -> {top['office']} {top['allowance_rate']}")
        bad = await client.call_tool(
            "ssa_alj_compare_offices", {"as_of": "x"}, raise_on_error=False
        )
        show("tools/call (bad args)", f"isError={bad.is_error}")

        resources = await client.list_resources()
        show("resources/list", [str(r.uri) for r in resources])
        content = await client.read_resource("ssa-alj://about")
        show("resources/read", content[0].text.splitlines()[0])

        prompts = await client.list_prompts()
        show("prompts/list", [p.name for p in prompts])
        prompt = await client.get_prompt("judge_summary", {"judge_name": "Smith"})
        show("prompts/get", prompt.messages[0].content.text)


# --------------------------------------------------------------------------- raw JSON-RPC (HTTP)


class RawSession:
    """Minimal Streamable-HTTP client: POST JSON-RPC to /mcp and keep the session header."""

    def __init__(self, url: str) -> None:
        self.url, self.session_id, self._id = url, None, 0

    def send(self, method: str, params: dict | None = None, notify: bool = False) -> Any:
        body: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            body["params"] = params
        if not notify:
            self._id += 1
            body["id"] = self._id
        headers = {
            "content-type": "application/json",
            "accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        req = urllib.request.Request(self.url, json.dumps(body).encode(), headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            self.session_id = resp.headers.get("mcp-session-id", self.session_id)
            raw = resp.read().decode()
        if notify or not raw:
            return None
        for line in raw.splitlines():  # event-stream framing: "data: {...}"
            if line.startswith("data:"):
                raw = line[5:]
        reply = json.loads(raw)
        return reply.get("result", reply.get("error"))

    def close(self) -> None:
        req = urllib.request.Request(
            self.url, method="DELETE", headers={"mcp-session-id": self.session_id or ""}
        )
        urllib.request.urlopen(req, timeout=10).read()


def run_raw(url: str) -> None:
    s = RawSession(url)
    init = s.send(
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "demo", "version": "0"},
        },
    )
    show("initialize", {"protocol": init["protocolVersion"], "server": init["serverInfo"]["name"]})
    s.send("notifications/initialized", notify=True)
    show("notifications/initialized", "sent (no response expected)")
    show("ping", s.send("ping"))
    show("tools/list", f"{len(s.send('tools/list')['tools'])} tools")
    res = s.send("tools/call", {"name": "ssa_alj_list_reports", "arguments": {}})
    show("tools/call", json.loads(res["content"][0]["text"])["coverage"]["fiscal_years"][:3])
    show("resources/list", [r["uri"] for r in s.send("resources/list")["resources"]])
    show(
        "resources/read",
        s.send("resources/read", {"uri": "ssa-alj://about"})["contents"][0]["text"][:60],
    )
    show("prompts/list", [p["name"] for p in s.send("prompts/list")["prompts"]])
    show(
        "prompts/get",
        s.send("prompts/get", {"name": "judge_summary", "arguments": {"judge_name": "Smith"}})[
            "messages"
        ][0]["content"]["text"],
    )
    s.close()
    show("DELETE /mcp (session close)", "ok")


class RawModern:
    """Stateless modern-era client: no handshake, protocol info travels in params._meta + headers."""

    VERSION = "2026-07-28"

    def __init__(self, url: str) -> None:
        self.url, self._id = url, 0

    def send(self, method: str, params: dict | None = None) -> Any:
        self._id += 1
        meta = {
            "io.modelcontextprotocol/protocolVersion": self.VERSION,
            "io.modelcontextprotocol/clientCapabilities": {},
        }
        body = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": method,
            "params": {**(params or {}), "_meta": meta},
        }
        headers = {
            "content-type": "application/json",
            "accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": self.VERSION,
            "Mcp-Method": method,
        }
        name = (params or {}).get("name") or (params or {}).get("uri")
        if name:
            headers["Mcp-Name"] = name
        req = urllib.request.Request(self.url, json.dumps(body).encode(), headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode()
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode()
        for line in raw.splitlines():
            if line.startswith("data:"):
                raw = line[5:]
        reply = json.loads(raw)
        return reply.get("result", reply.get("error"))


def run_raw_modern(url: str) -> None:
    s = RawModern(url)
    d = s.send("server/discover")
    show(
        "server/discover",
        {
            "versions": d["supportedVersions"],
            "server": d["_meta"]["io.modelcontextprotocol/serverInfo"]["name"],
        },
    )
    show("ping", s.send("ping"))
    show("tools/list", f"{len(s.send('tools/list')['tools'])} tools")
    res = s.send("tools/call", {"name": "ssa_alj_list_reports", "arguments": {}})
    show("tools/call", json.loads(res["content"][0]["text"])["coverage"]["fiscal_years"][:3])
    show("resources/list", [r["uri"] for r in s.send("resources/list")["resources"]])
    show(
        "resources/read",
        s.send("resources/read", {"uri": "ssa-alj://about"})["contents"][0]["text"][:60],
    )
    show("prompts/list", [p["name"] for p in s.send("prompts/list")["prompts"]])
    show(
        "prompts/get",
        s.send("prompts/get", {"name": "judge_summary", "arguments": {"judge_name": "Smith"}})[
            "messages"
        ][0]["content"]["text"],
    )
    show("(no DELETE / session)", "modern era is stateless")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--url", help="Streamable-HTTP endpoint, e.g. http://127.0.0.1:8000/mcp (default: stdio)"
    )
    ap.add_argument(
        "--raw", action="store_true", help="send raw JSON-RPC over HTTP instead of the SDK client"
    )
    ap.add_argument(
        "--modern", action="store_true", help="with --raw: use the modern (2026-07-28) era"
    )
    ap.add_argument(
        "--legacy", action="store_true", help="SDK client: force the initialize handshake"
    )
    args = ap.parse_args()
    if args.raw:
        if not args.url:
            ap.error("--raw needs --url")
        (run_raw_modern if args.modern else run_raw)(args.url)
    else:
        asyncio.run(run_sdk(args.url, args.legacy))
    return 0


if __name__ == "__main__":
    sys.exit(main())
