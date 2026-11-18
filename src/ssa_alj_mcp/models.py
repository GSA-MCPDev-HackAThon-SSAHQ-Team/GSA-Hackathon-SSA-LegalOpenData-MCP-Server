"""Pydantic models and TypedDicts shared by tools and services.

Tool signatures use these Annotated aliases and enums so MCP clients (and LLMs) see
structured, validated inputs — not free-form strings for every parameter.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, Field

# --- Scalar aliases (validated inputs) ----------------------------------------

FiscalYear = Annotated[
    int,
    Field(
        description=(
            "US federal fiscal year (Oct 1 - Sep 30), e.g. 2024. "
            "Omit on snapshot tools to use the latest FY-final disposition snapshot."
        ),
        ge=2000,
        le=2100,
    ),
]
PeriodEnd = Annotated[
    str,
    Field(
        description="Snapshot period end as ISO date YYYY-MM-DD, e.g. '2024-09-27'.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
]
RegionCode = Annotated[
    str,
    Field(
        description="SSA region code, e.g. '04' (digits are zero-padded). Example: '02'.",
        max_length=2,
    ),
]
OfficeQuery = Annotated[
    str,
    Field(
        description="Hearing office name or city fragment, e.g. 'Miami' or 'QUEENS'.",
        min_length=1,
        max_length=100,
    ),
]
JudgeNameQuery = Annotated[
    str,
    Field(
        description=(
            "Published judge name or fragment, e.g. 'Cartledge' or 'Adams, Ann'. "
            "Case/punctuation folded; SSA publishes no judge ID."
        ),
        min_length=1,
        max_length=100,
    ),
]

# --- Shared enums / literals (agent-facing choices) ---------------------------

OfficeSortKey = Literal[
    "allowance_rate",
    "denial_rate",
    "total_decisions",
    "total_dispositions",
    "judges",
    "dispositions_per_judge",
]
TrendGroupBy = Literal["national", "region"]
EntityLevel = Literal["office", "region", "judge"]
PeerLevel = Literal["office", "judge"]
OutlierMeasure = Literal["allowance_rate", "non_decision_share", "dispositions"]
PeriodSortKey = Literal[
    "allowance_rate_change",
    "dispositions_change_pct",
    "decisions_change_pct",
]
PeriodDirection = Literal["largest_move", "increase", "decrease"]
VariationSortKey = Literal["gap", "stdev", "judges"]


class ResponseFormat(str, Enum):
    """How a tool should shape its return value."""

    JSON = "json"
    MARKDOWN = "markdown"


class PaginationParams(BaseModel):
    """Reusable pagination inputs for list-style tools (default page size 25)."""

    limit: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Maximum items to return (1-100). Default 25.",
    )
    offset: int = Field(default=0, ge=0, description="Items to skip from the start. Example: 0.")


class SnapshotRefDict(TypedDict):
    """`snapshot` object on successful tool payloads that use one report period."""

    period_end: str
    fiscal_year: int
    report: str


class SnapshotRef(BaseModel):
    """Pydantic twin of SnapshotRefDict (period the numbers are 'as of')."""

    period_end: str = Field(description="ISO period end YYYY-MM-DD.")
    fiscal_year: int = Field(description="Federal fiscal year of the snapshot.")
    report: str = Field(description="SSA report label, e.g. 'September'.")


class ToolError(BaseModel):
    """Sanitised error payload returned inside tool results (not a protocol error)."""

    error: str
    hint: str | None = None

    model_config = {"extra": "allow"}


class PageEnvelope(BaseModel):
    """Standard list response shape produced by `utils.paginate`."""

    total: int
    count: int
    offset: int
    has_more: bool
    next_offset: int | None
    items: list[Any]
    notes: list[str] = Field(default_factory=list)


# Documented output contracts (for judges / agents — tools return dicts matching these shapes).
OUTPUT_CONTRACT = """
Successful tool payloads are JSON objects (or Markdown when response_format=markdown):
- List tools: {total, count, offset, has_more, next_offset, items, notes?}
- Snapshot-scoped tools also include: snapshot {period_end, fiscal_year, report}
- Failures inside the tool result: {error, hint?, ...} — never a raw stack trace
- Domain caveats appear in notes[] (FYTD semantics, case-mix, name matching)
"""
