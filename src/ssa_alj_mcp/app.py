"""MCP server entry point (kept thin: build FastMCP, register parts, pick a transport)."""

from __future__ import annotations

import os

from fastmcp import FastMCP

from ssa_alj_mcp.config import settings
from ssa_alj_mcp.logging_config import configure_logging, get_logger
from ssa_alj_mcp.prompts import register_prompts
from ssa_alj_mcp.resources import register_resources
from ssa_alj_mcp.routes import register_routes
from ssa_alj_mcp.tools import register_tools

configure_logging()
log = get_logger(__name__)

mcp = FastMCP(
    name="SSA ALJ Open Data",
    instructions=(
        "Public SSA Office of Hearings Operations ALJ disposition data (FY 2010 onward). "
        "Thirteen tools cover coverage, judges, offices, rankings, trends, outliers, and "
        "data-quality notes. Counts are fiscal-year-to-date; the September snapshot is the "
        "full year. Match judges by published name only. Always cite report 'as of' dates. "
        "Allowance rates are not case-mix adjusted and are not performance ratings."
    ),
)

register_tools(mcp)
register_prompts(mcp)
register_resources(mcp)
register_routes(mcp)


def main() -> None:
    """stdio locally; HTTP when a platform injects PORT or MCP_TRANSPORT=streamable-http."""
    platform_port = os.getenv("PORT")
    if platform_port:
        log.info("starting HTTP transport on 0.0.0.0:%s", platform_port)
        mcp.run(transport="http", host="0.0.0.0", port=int(platform_port))
    elif settings.mcp_transport == "streamable-http":
        log.info("starting streamable-http on %s:%s", settings.mcp_host, settings.mcp_port)
        mcp.run(transport="streamable-http", host=settings.mcp_host, port=settings.mcp_port)
    else:
        log.info("starting stdio transport")
        mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
