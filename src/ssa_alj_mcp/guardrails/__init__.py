"""Input guardrails for free-text tool arguments.

Add a rule in `rules.py`, then cover it in `tests/test_guardrails.py`.
The matched text is never returned or logged.
"""

from __future__ import annotations

from ssa_alj_mcp.guardrails.rules import refusal, scope_note

__all__ = ["refusal", "scope_note"]
