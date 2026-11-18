"""Guardrail rules.

Two kinds:

- `scope_note` is advisory. A forecast or "best performer" question still gets recipes,
  plus a note that the dataset cannot answer it that way.
- `refusal` stops the tool. Personal data and attempts to break out of this read-only
  server are not echoed back.

To add a rule: append one `_Rule` with a stable id, and add a test that the reply does
not contain the sample input.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ssa_alj_mcp.logging_config import get_logger
from ssa_alj_mcp.utils import error

log = get_logger(__name__)

_SCOPE_NOTE_FORECAST = (
    "This dataset has no forecasting model. Published counts are cumulative fiscal-year-to-date "
    "figures, so they cannot predict a future year. Use the factual recipes below (trends, "
    "outliers, or a judge profile) and describe what happened, not what will happen."
)
_SCOPE_NOTE_RANKING = (
    "Published allowance and decision counts are not a performance rating for any ALJ or office, "
    "and allowance rates are not case-mix adjusted. Do not name a 'best' or 'top' judge from "
    "these tools. Use outlier_report or within_office_variation for factual comparisons."
)

_PII_MESSAGE = (
    "This server only answers questions about published ALJ disposition counts. "
    "Do not send Social Security numbers, dates of birth, contact details, medical information, "
    "or other personal data."
)
_SECURITY_MESSAGE = (
    "That input is not a question about published dispositions. "
    "This server is read-only and does not run instructions embedded in tool arguments."
)


@dataclass(frozen=True)
class _Rule:
    id: str
    pattern: re.Pattern[str]
    category: str  # "pii" or "security"


def _rule(rule_id: str, pattern: str, category: str) -> _Rule:
    return _Rule(rule_id, re.compile(pattern, re.IGNORECASE), category)


_FORECAST_RE = re.compile(
    r"\b(predict\w*|forecast\w*|projection\w*|project(ed|ing|s)?|next (year|fiscal)|"
    r"future|will|going to)\b",
    re.IGNORECASE,
)
_BEST_PERFORMER_RE = re.compile(
    r"\b((best|top|worst)[ -](performers?|performing|judges?|performance)|"
    r"judge (performance )?rank(ing|ings|s)?)\b",
    re.IGNORECASE,
)

_REFUSALS: tuple[_Rule, ...] = (
    _rule("pii.ssn", r"\b\d{3}-\d{2}-\d{4}\b", "pii"),
    _rule("pii.ssn_words", r"\b(ssn|social security number)\b", "pii"),
    _rule("pii.dob", r"\b(date of birth|d\.?o\.?b\.?)\b", "pii"),
    _rule("pii.contact", r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", "pii"),
    _rule(
        "pii.phone",
        r"\b(?:\+?1[-.\s])?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b",
        "pii",
    ),
    _rule(
        "pii.medical",
        r"\b(medical record|diagnosis|patient history|claimant address)\b",
        "pii",
    ),
    _rule(
        "security.instructions",
        r"\bignore\s+(all\s+|any\s+)?(previous|prior|above)\s+(instructions|prompts)\b",
        "security",
    ),
    _rule(
        "security.prompt",
        r"\breveal\s+(your\s+|the\s+)?(system|developer)\s+(prompt|instructions)\b",
        "security",
    ),
    _rule(
        "security.sql",
        r"\b(union\s+select|drop\s+table|delete\s+from|insert\s+into|or\s+1\s*=\s*1)\b",
        "security",
    ),
    _rule("security.path", r"(\.\./|/etc/passwd)", "security"),
)


def scope_note(query_text: str | None) -> str | None:
    """Advisory note for a forecast or a performance ranking. Does not refuse the call."""
    if not query_text:
        return None
    notes: list[str] = []
    if _FORECAST_RE.search(query_text):
        notes.append(_SCOPE_NOTE_FORECAST)
    if _BEST_PERFORMER_RE.search(query_text):
        notes.append(_SCOPE_NOTE_RANKING)
    return " ".join(notes) or None


def refusal(*values: str | None) -> dict | None:
    """Error payload when any value trips a PII or security rule. None when all are clear.

    The returned text names the rule id only. It does not repeat the input.
    """
    for value in values:
        if not value:
            continue
        for rule in _REFUSALS:
            if rule.pattern.search(value):
                log.warning("guardrail refused rule=%s", rule.id)
                message = _PII_MESSAGE if rule.category == "pii" else _SECURITY_MESSAGE
                return error(message, "Ask about a published office, judge, year, or rate.", rule_id=rule.id)
    return None
