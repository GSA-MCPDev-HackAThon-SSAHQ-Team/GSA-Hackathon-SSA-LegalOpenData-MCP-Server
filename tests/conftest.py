"""Fixtures: a tiny synthetic SQLite DB built from db/schema.sql (no network, no real data)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ssa_alj_mcp.config import PROJECT_ROOT, settings

# (snapshot_id, fiscal_year, period_end, label)
SNAPSHOTS = [
    (1, 2023, "2023-06-30", "June"),  # earlier snapshot of FY2023 (must be ignored)
    (2, 2023, "2023-09-29", "September"),  # FY2023 final
    (3, 2024, "2024-09-27", "September"),  # FY2024 final
]
JUDGES = [
    (1, "Adams, Ann", "adams ann"),
    (2, "Baker, Bob", "baker bob"),
    (3, "Baker, Bob.", "baker bob"),
    (4, "Clark, Cy", "clark cy"),
]
OFFICES = [(1, "MIAMI OHO"), (2, "MIAMI, FL"), (3, "ATLANTA NORTH"), (4, "ATLANTA DOWNTOWN")]
# snapshot, row, alj, office, region, ff, pf, den, dispositions
ROWS = [
    (1, 1, 1, 1, "04", 10, 0, 10, 25),
    (2, 1, 1, 1, "04", 60, 20, 20, 120),
    (2, 2, 4, 3, "04", 30, 10, 60, 120),
    (3, 1, 1, 2, "04", 50, 10, 40, 110),
    (3, 2, 2, 3, "04", 20, 0, 80, 110),
    (3, 3, 4, 4, "04", 5, 0, 5, 12),
]


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript((PROJECT_ROOT / "db" / "schema.sql").read_text())
    for sid, fy, end, label in SNAPSHOTS:
        conn.execute(
            "INSERT INTO report_snapshot (snapshot_id, report_kind, source_xml_url, fiscal_year, report_label, "
            "reporting_period_end, loaded_row_count) VALUES (?, 'alj_disposition', ?, ?, ?, ?, 0)",
            (sid, f"https://example.test/{sid}.xml", fy, label, end),
        )
    conn.execute(
        "INSERT INTO report_snapshot (snapshot_id, report_kind, source_xml_url, fiscal_year, report_label, "
        "reporting_period_end, loaded_row_count) VALUES (9, 'office_ranking', 'https://example.test/r.xml', "
        "2024, 'March', '2024-03-29', 2)"
    )
    conn.execute("INSERT INTO region VALUES ('04')")
    conn.executemany("INSERT INTO alj (alj_id, name_raw, name_key) VALUES (?, ?, ?)", JUDGES)
    conn.executemany("INSERT INTO hearing_office VALUES (?, ?)", OFFICES)
    for sid, n, alj, off, reg, ff, pf, den, disp in ROWS:
        conn.execute(
            "INSERT INTO alj_disposition (snapshot_id, row_number, alj_id, office_id, region_code, fully_favorable, "
            "partially_favorable, total_awards, total_denials, total_decisions, total_dispositions) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (sid, n, alj, off, reg, ff, pf, ff + pf, den, ff + pf + den, disp),
        )
    conn.execute("INSERT INTO office_ranking VALUES (9, 1, '04', 1, 2.5, 120, NULL)")
    conn.execute("INSERT INTO office_ranking VALUES (9, 3, '04', 2, 2.1, 120, NULL)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(settings, "ssa_alj_db_path", path)
    return path
