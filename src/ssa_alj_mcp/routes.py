"""HTTP-only infrastructure routes (active with the streamable-http transport)."""

from __future__ import annotations

from html import escape

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from ssa_alj_mcp import __version__
from ssa_alj_mcp.config import settings
from ssa_alj_mcp.db import DatabaseUnavailable, connect
from ssa_alj_mcp.logging_config import get_logger

log = get_logger(__name__)


def public_origin(request: Request) -> str:
    """Scheme and host the visitor used.

    Behind Render the app sees plain HTTP, so the public scheme comes from
    X-Forwarded-Proto. The host stays correct when a custom domain points here.
    """
    forwarded = request.headers.get("x-forwarded-proto", "")
    scheme = forwarded.split(",")[0].strip() or request.url.scheme
    host = request.headers.get("host") or request.url.netloc
    return f"{scheme}://{host}"


def public_mcp_url(request: Request) -> str:
    """URL a browser visitor should paste into an MCP client."""
    return f"{public_origin(request)}/mcp"


def _tool_rows(tools: list) -> str:
    rows: list[str] = []
    for tool in tools:
        title = ""
        annotations = getattr(tool, "annotations", None)
        if annotations is not None:
            title = getattr(annotations, "title", None) or ""
        if not title:
            title = (getattr(tool, "description", None) or "").strip().split("\n", 1)[0]
        name = escape(tool.name, quote=True)
        desc = escape(title, quote=True)
        rows.append(f"<tr><td class=\"name\"><code>{name}</code></td><td>{desc}</td></tr>")
    return "\n".join(rows)


def _home_page(mcp_url: str, health_url: str, tools: list) -> str:
    mcp = escape(mcp_url, quote=True)
    health = escape(health_url, quote=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SSA ALJ Open Data</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1c1917;
      --muted: #57534e;
      --paper: #f7f6f3;
      --line: #e7e5e4;
      --card: #fffcf7;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: "Iowan Old Style", Palatino, Georgia, serif;
    }}
    main {{
      width: min(46rem, calc(100% - 2.5rem));
      margin: 0 auto;
      padding: 3.25rem 0 4rem;
    }}
    p, h2 {{
      margin: 0;
      color: var(--muted);
      font-family: ui-sans-serif, system-ui, sans-serif;
      font-size: 0.95rem;
      font-weight: 400;
    }}
    h1 {{
      margin: 0.4rem 0 1.75rem;
      font-size: 1.85rem;
      font-weight: 500;
      letter-spacing: -0.02em;
    }}
    h2 {{ margin: 2.25rem 0 0.7rem; }}
    .url {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.85rem 0.9rem;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 0.7rem;
    }}
    .url + .url {{ margin-top: 0.55rem; }}
    .label {{
      flex: none;
      width: 3.6rem;
      color: var(--muted);
      font-family: ui-sans-serif, system-ui, sans-serif;
      font-size: 0.72rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    code, a {{
      font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
      font-size: 0.92rem;
      word-break: break-all;
    }}
    a {{ flex: 1; color: inherit; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    #mcp-url {{ flex: 1; }}
    button {{
      flex: none;
      border: 0;
      background: transparent;
      color: var(--ink);
      font: 0.85rem ui-sans-serif, system-ui, sans-serif;
      cursor: pointer;
      padding: 0.2rem 0.15rem;
    }}
    button:hover {{ text-decoration: underline; }}
    .note {{ margin-top: 0.7rem; font-size: 0.8rem; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 0.7rem;
      overflow: hidden;
    }}
    th, td {{
      text-align: left;
      vertical-align: top;
      padding: 0.7rem 0.9rem;
      border-bottom: 1px solid var(--line);
      font-family: ui-sans-serif, system-ui, sans-serif;
      font-size: 0.92rem;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    th {{
      color: var(--muted);
      font-weight: 500;
      font-size: 0.75rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    td.name {{ width: 46%; }}
    td.name code {{ font-size: 0.8rem; }}
  </style>
</head>
<body>
  <main>
    <p>MCP server</p>
    <h1>SSA ALJ Open Data</h1>
    <div class="url">
      <span class="label">MCP</span>
      <code id="mcp-url">{mcp}</code>
      <button type="button" id="copy">Copy</button>
    </div>
    <div class="url">
      <span class="label">Health</span>
      <a href="{health}">{health}</a>
    </div>
    <p class="note">No trailing slash on the MCP URL. Health returns JSON.</p>
    <h2>Tools</h2>
    <table>
      <thead><tr><th>Tool</th><th>Description</th></tr></thead>
      <tbody>
        {_tool_rows(tools)}
      </tbody>
    </table>
  </main>
  <script>
    const button = document.getElementById("copy");
    const urlNode = document.getElementById("mcp-url");
    function selectUrl() {{
      const range = document.createRange();
      range.selectNodeContents(urlNode);
      const selection = getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
    }}
    button.addEventListener("click", async () => {{
      const url = urlNode.textContent;
      let copied = false;
      try {{
        await navigator.clipboard.writeText(url);
        copied = true;
      }} catch (err) {{
        selectUrl();
        try {{ copied = document.execCommand("copy"); }} catch (e) {{ copied = false; }}
      }}
      button.textContent = copied ? "Copied" : "Selected";
      setTimeout(() => {{ button.textContent = "Copy"; }}, 1600);
    }});
  </script>
</body>
</html>
"""


def register_routes(mcp: FastMCP) -> None:
    @mcp.custom_route("/", methods=["GET"])
    async def home(request: Request) -> HTMLResponse:
        origin = public_origin(request)
        tools = await mcp.list_tools()
        page = _home_page(f"{origin}/mcp", f"{origin}/health", list(tools))
        return HTMLResponse(page)

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        # Fast path for platforms: always returns JSON; db_ok says whether tools can run.
        db_ok = False
        db_error = None
        try:
            with connect() as conn:
                conn.execute("SELECT 1 FROM report_snapshot LIMIT 1").fetchone()
            db_ok = True
        except DatabaseUnavailable as exc:
            db_error = str(exc)
            log.warning("health: database unavailable: %s", exc)
        except Exception as exc:  # pragma: no cover - defensive
            db_error = "database query failed"
            log.warning("health: unexpected database error: %s", exc)

        body = {
            "status": "healthy" if db_ok else "degraded",
            "service": "ssa-alj-mcp",
            "db_ok": db_ok,
            "db_path": str(settings.ssa_alj_db_path),
        }
        if db_error and not db_ok:
            body["db_error"] = db_error
        # 200 even when degraded so platforms that only check HTTP status still see the app up;
        # operators should read db_ok.
        return JSONResponse(body)

    @mcp.custom_route("/version", methods=["GET"])
    async def version(request: Request) -> JSONResponse:
        return JSONResponse({"version": __version__})
