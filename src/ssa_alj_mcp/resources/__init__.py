"""Resources: static reference material the client can read directly."""

from __future__ import annotations

from fastmcp import FastMCP

from ssa_alj_mcp.resources import about


def register_resources(mcp: FastMCP) -> None:
    about.register(mcp)
