"""Shared MCP annotations/helpers for tool modules (no SQL, no services imports)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from ssa_alj_mcp.formatting import ensure_notes, format_response
from ssa_alj_mcp.guardrails import refusal
from ssa_alj_mcp.models import PaginationParams, ResponseFormat

READ_ONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,  # fixed local dataset, no outbound calls
}

# Client-facing groups (FastMCP tags + meta.category). Keep in sync with resources/about.py.
DISCOVERY = "discovery"
LOOKUP = "lookup"
ANALYSIS = "analysis"


def tool_group(category: str) -> dict[str, Any]:
    """Kwargs for @mcp.tool: tags={category}, meta={category: …}."""
    return {"tags": {category}, "meta": {"category": category}}

ResponseFormatParam = Annotated[
    ResponseFormat,
    Field(
        description=(
            "Response shape: 'json' (default, machine-readable) or 'markdown' (human summary). "
            "Example: 'json'."
        )
    ),
]


def refusal_for(*values: str | None) -> dict[str, Any] | None:
    """PII or security refusal for free-text arguments. None when the text is clear."""
    return refusal(*values)


def annotations(title: str) -> dict:
    return {"title": title, **READ_ONLY}


def page_args(pagination: PaginationParams | None) -> tuple[int, int]:
    p = pagination or PaginationParams()
    return p.limit, p.offset


def shaped(
    payload: dict[str, Any],
    response_format: ResponseFormat,
    *,
    title: str,
) -> dict[str, Any] | str:
    return format_response(ensure_notes(payload), response_format, title=title)
