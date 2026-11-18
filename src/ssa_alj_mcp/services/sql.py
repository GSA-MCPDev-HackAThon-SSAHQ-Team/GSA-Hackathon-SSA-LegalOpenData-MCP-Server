"""Shared SQL fragments for disposition aggregates.

Domain/SQL concerns live here (not in utils.py). Service modules import these instead of
inlining the same SUM(...) list.
"""

from __future__ import annotations

SUM_FIELDS = (
    "fully_favorable",
    "partially_favorable",
    "total_awards",
    "total_denials",
    "total_decisions",
    "total_dispositions",
)

SUM_COLUMNS = """
    SUM(d.fully_favorable)    AS fully_favorable,
    SUM(d.partially_favorable) AS partially_favorable,
    SUM(d.total_awards)       AS total_awards,
    SUM(d.total_denials)      AS total_denials,
    SUM(d.total_decisions)    AS total_decisions,
    SUM(d.total_dispositions) AS total_dispositions
"""

# Join disposition rows to the fiscal-year-final snapshot view (one row per FY).
JOIN_FY_FINAL = (
    "FROM alj_disposition d "
    "JOIN alj a ON a.alj_id = d.alj_id "
    "JOIN v_fy_final_snapshot s ON s.snapshot_id = d.snapshot_id "
)

JOIN_HEARING_OFFICE = "JOIN hearing_office o ON o.office_id = d.office_id "
