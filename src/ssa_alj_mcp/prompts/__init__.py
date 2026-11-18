"""Prompts: reusable conversation starters."""

from __future__ import annotations

from fastmcp import FastMCP

from ssa_alj_mcp.prompts import analysis


def register_prompts(mcp: FastMCP) -> None:
    analysis.register(mcp)
