"""Pure helpers: pagination, error payloads, name normalisation, rates.

No database or MCP imports here, so these are trivially unit-testable.
`formatting.py` shapes MCP responses; `services/common.py` holds domain/SQL helpers.
"""

from __future__ import annotations

import re
from typing import Any

from ssa_alj_mcp.config import settings
from ssa_alj_mcp.models import PageEnvelope, ToolError


def error(message: str, hint: str | None = None, **extra: Any) -> dict[str, Any]:
    """Actionable, sanitised error payload (never a stack trace)."""
    payload = ToolError(error=message, hint=hint, **extra)
    return payload.model_dump(exclude_none=True)


def normalize_key(text: str) -> str:
    """Lower-case, punctuation-free key (matches `alj.name_key` written by the loader)."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", text.lower())).strip()


def clamp_page(limit: int, offset: int) -> tuple[int, int]:
    """Clamp limit to [1, max_page_size] and offset to >= 0."""
    return max(1, min(int(limit), settings.max_page_size)), max(0, int(offset))


def paginate(items: list[Any], limit: int, offset: int) -> dict[str, Any]:
    """Slice a list and return the standard PageEnvelope dict."""
    limit, offset = clamp_page(limit, offset)
    page = items[offset : offset + limit]
    has_more = offset + len(page) < len(items)
    # notes is optional on the wire; omit the empty default so list payloads stay lean.
    return PageEnvelope(
        total=len(items),
        count=len(page),
        offset=offset,
        has_more=has_more,
        next_offset=offset + len(page) if has_more else None,
        items=page,
    ).model_dump(exclude_defaults=True)


def rate(numerator: float | None, denominator: float | None) -> float | None:
    """numerator / denominator rounded to 4 decimals, or None if undefined."""
    if not denominator or numerator is None:
        return None
    return round(numerator / denominator, 4)
