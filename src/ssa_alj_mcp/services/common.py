"""Domain helpers shared by query services (SQLite + SSA FYTD semantics).

Layering (keep these boundaries sharp):
- `ssa_alj_mcp.utils` — pure helpers (paginate, error, normalize_key, rate); no DB/MCP.
- `ssa_alj_mcp.services.common` — domain/SQL helpers (snapshots, enrich, handled); uses DB.
- `ssa_alj_mcp.services.sql` — shared SQL fragments (SUM_COLUMNS, joins).
- `ssa_alj_mcp.formatting` — MCP response shaping (JSON vs Markdown).

Import pure helpers from `utils` directly in service modules; this module does not re-export them.
"""

from __future__ import annotations

import functools
import sqlite3
from collections.abc import Callable
from datetime import date
from typing import Any

from ssa_alj_mcp.db import DatabaseUnavailable, query, query_one
from ssa_alj_mcp.models import SnapshotRefDict
from ssa_alj_mcp.services.sql import SUM_FIELDS
from ssa_alj_mcp.utils import error

# Appears in every response that contains disposition counts so the model cannot miss it.
CUMULATIVE_NOTE = (
    "Counts are cumulative fiscal-year-to-date as of the snapshot's period end "
    "(the US federal fiscal year runs Oct 1 - Sep 30). Do not add figures from different snapshots "
    "of the same fiscal year; the September snapshot holds the full-year totals."
)
RATE_NOTE = (
    "allowance_rate = (fully + partially favorable) / total_decisions; denial_rate = denials / "
    "total_decisions. other_dispositions = total_dispositions - total_decisions (non-decision "
    "outcomes such as dismissals) and is excluded from both rates."
)


def handled(fn: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    """Wrap a service function so DB failures become error payloads instead of exceptions."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return fn(*args, **kwargs)
        except DatabaseUnavailable:
            return error(
                "The SSA ALJ database is not available on this server.",
                "Build it with: uv run --group etl data/scripts/crawl_ssa_alj.py && "
                "uv run data/scripts/load_ssa_alj.py (or set SSA_ALJ_DB_PATH).",
            )
        except sqlite3.Error:
            return error(
                "The database query failed.", "Retry; if it persists, rebuild the database."
            )

    return wrapper


def enrich(row: dict[str, Any]) -> dict[str, Any]:
    """Add derived measures (rates, other_dispositions) to an aggregated sum row."""
    from ssa_alj_mcp.utils import rate

    out = dict(row)
    dec, dis = row.get("total_decisions"), row.get("total_dispositions")
    out["other_dispositions"] = dis - dec if dis is not None and dec is not None else None
    out["allowance_rate"] = rate(row.get("total_awards"), dec)
    out["denial_rate"] = rate(row.get("total_denials"), dec)
    return out


def snapshot_ref(snap: dict[str, Any]) -> SnapshotRefDict:
    """Standard `snapshot` object returned by tools that use one report period.

    When the row includes SSA URLs, attach `sources: {html?, xml?}` so answers are
    checkable on ssa.gov without a separate call.
    """
    ref: SnapshotRefDict = {
        "period_end": snap["reporting_period_end"],
        "fiscal_year": snap["fiscal_year"],
        "report": snap["report_label"],
    }
    sources: dict[str, str] = {}
    if snap.get("source_html_url"):
        sources["html"] = snap["source_html_url"]
    if snap.get("source_xml_url"):
        sources["xml"] = snap["source_xml_url"]
    if sources:
        ref["sources"] = sources
    return ref


def available_fiscal_years() -> list[int]:
    """Fiscal years that have a final (or latest) disposition snapshot, ascending."""
    return [
        r["fiscal_year"] for r in query("SELECT fiscal_year FROM v_fy_final_snapshot ORDER BY 1")
    ]


def resolve_snapshot(
    fiscal_year: int | None, as_of: str | None
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Pick the disposition snapshot to report on.

    Priority: explicit `as_of` period end > the final snapshot of `fiscal_year` > newest final
    snapshot. Returns (snapshot, None) or (None, error_payload).
    """
    columns = (
        "snapshot_id, fiscal_year, reporting_period_end, report_label, "
        "source_xml_url, source_html_url"
    )
    if as_of:
        try:
            date.fromisoformat(as_of)
        except ValueError:
            return None, error(
                "as_of must be an ISO date (YYYY-MM-DD).",
                "Use ssa_alj_list_reports to see valid period ends.",
            )
        snap = query_one(
            f"SELECT {columns} FROM report_snapshot WHERE report_kind = 'alj_disposition' "
            "AND reporting_period_end = ? ORDER BY loaded_row_count DESC, snapshot_id LIMIT 1",
            (as_of,),
        )
        if snap is None:
            return None, error(
                f"No disposition report ends on {as_of}.",
                "Use ssa_alj_list_reports (with fiscal_year) to see the available period ends.",
            )
        return snap, None
    if fiscal_year is not None:
        snap = query_one(
            f"SELECT {columns} FROM v_fy_final_snapshot WHERE fiscal_year = ?", (fiscal_year,)
        )
        if snap is None:
            return None, error(
                f"No disposition data for fiscal year {fiscal_year}.",
                f"Available fiscal years: {available_fiscal_years()}",
            )
        return snap, None
    snap = query_one(
        f"SELECT {columns} FROM v_fy_final_snapshot ORDER BY reporting_period_end DESC LIMIT 1"
    )
    if snap is None:  # empty database
        return None, error("The database contains no disposition reports.", "Run the load script.")
    return snap, None


def normalize_region(region: str | None) -> str | None:
    """Pad numeric region codes to two digits (`4` -> `04`); pass through named regions."""
    if region is None or not region.strip():
        return None
    r = region.strip()
    return r.zfill(2) if r.isdigit() else r


def in_clause(values: list[Any]) -> str:
    """Return `?,?,?` placeholders matching `values` length for a SQL IN clause."""
    return ",".join("?" for _ in values)


def zero_sums() -> dict[str, int]:
    """Zero-initialised dict for the six disposition count columns."""
    return dict.fromkeys(SUM_FIELDS, 0)


def add_sums(acc: dict[str, Any], row: dict[str, Any]) -> None:
    """Add one row's disposition counts into an accumulator (mutates `acc`)."""
    for f in SUM_FIELDS:
        acc[f] += row.get(f) or 0


def non_decision_share(row: dict[str, Any]) -> float | None:
    """Share of dispositions that are not decisions (dismissals, etc.), or None if unknown."""
    disp, dec = row.get("total_dispositions"), row.get("total_decisions")
    if not disp or dec is None:
        return None
    return round((disp - dec) / disp, 4)


def pts(new: float | None, old: float | None) -> float | None:
    """Difference of two rates in percentage points."""
    if new is None or old is None:
        return None
    return round((new - old) * 100, 1)


def pct_change(new: float | None, old: float | None) -> float | None:
    """Percent change from `old` to `new`, or None if `old` is zero/missing."""
    if new is None or not old:
        return None
    return round((new - old) / old * 100, 1)


__all__ = [
    "CUMULATIVE_NOTE",
    "RATE_NOTE",
    "add_sums",
    "available_fiscal_years",
    "enrich",
    "handled",
    "in_clause",
    "non_decision_share",
    "normalize_region",
    "pct_change",
    "pts",
    "resolve_snapshot",
    "snapshot_ref",
    "zero_sums",
]
