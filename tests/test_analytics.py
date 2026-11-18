"""Tests for trend, pace, comparison, outlier, variation, movement and quality tools."""

from __future__ import annotations

import pytest

from ssa_alj_mcp.config import settings
from ssa_alj_mcp.services import analysis, quality, trends, workforce


def test_national_trend_series_and_change(db_path):
    r = trends.national_trend()
    assert [s["fiscal_year"] for s in r["series"]] == [2023, 2024]
    assert r["series"][0]["allowance_rate_change_pts"] is None
    assert r["series"][1]["judges"] == 3
    assert r["series"][1]["allowance_rate_change_pts"] is not None
    assert r["highlights"]["peak_judges"]["fiscal_year"] == 2024


def test_national_trend_by_region_and_empty(db_path):
    assert {s["region"] for s in trends.national_trend(group_by="region")["series"]} == {"04"}
    assert "error" in trends.national_trend(region="09")
    assert "error" in trends.national_trend(group_by="bogus")


def test_monthly_pace_differences_cumulative_snapshots(db_path):
    r = trends.monthly_pace(fiscal_year=2023)
    first, second = r["periods"]
    assert first["dispositions_in_period"] == 25 and first["days_covered"] == 273
    assert second["dispositions_in_period"] == 240 - 25
    assert any("days" in f for f in second["flags"])  # 91-day gap is flagged


def test_monthly_pace_office_filter(db_path):
    r = trends.monthly_pace(fiscal_year=2023, office="miami")
    assert r["offices_matched"] == ["MIAMI OHO", "MIAMI, FL"]
    assert r["periods"][-1]["fytd_dispositions"] == 120
    assert "error" in trends.monthly_pace(office="nowhere")


def test_compare_periods_single_entity(db_path):
    r = trends.compare_periods("judge", 2023, 2024, name="adams")
    assert r["name"] == "Adams, Ann"
    assert r["change"]["allowance_rate_change_pts"] == pytest.approx(-20.0, abs=0.1)  # 0.8 -> 0.6


def test_compare_periods_ranking_excludes_one_sided_offices(db_path):
    r = trends.compare_periods("office", 2023, 2024, min_decisions=1)
    assert {i["name"] for i in r["items"]} == {"MIAMI", "ATLANTA NORTH"}
    assert r["excluded"]["present_only_in_second_year"] == 1  # ATLANTA DOWNTOWN
    assert "error" in trends.compare_periods("office", 1999, 2024)
    assert "error" in trends.compare_periods("planet", 2023, 2024)


def test_outlier_report_needs_enough_peers(db_path):
    r = analysis.outlier_report(level="office", min_decisions=1)
    assert "error" in r  # only a handful of offices in the synthetic data
    assert "error" in analysis.outlier_report(measure="bogus")


def test_within_office_variation_filters(db_path):
    r = analysis.within_office_variation(fiscal_year=2024, min_decisions=1, min_judges=2)
    assert r["total"] == 0  # no synthetic office has two judges in FY2024
    assert "error" in analysis.within_office_variation(office="nowhere")


def test_judge_movements(db_path):
    r = workforce.judge_movements(2023, 2024)
    s = r["summary"]
    assert (s["judges_from"], s["judges_to"]) == (2, 3)
    assert (s["stayed"], s["moved"], s["new_in_data"], s["left_data"]) == (1, 1, 1, 0)
    assert [m["judge"] for m in r["moved_judges"]["items"]] == ["Clark, Cy"]
    assert "error" in workforce.judge_movements(1999, 2024)


def test_data_quality_notes(db_path):
    r = quality.data_quality_notes()
    assert r["coverage"]["fiscal_years"] == [2023, 2024]
    issues = {g["fiscal_year"] for g in r["snapshot_gaps"]}
    assert issues == {2023, 2024}
    assert r["not_in_dataset"]


@pytest.mark.skipif(not settings.ssa_alj_db_path.exists(), reason="real database not built")
def test_real_database_known_findings():
    # Facts verified directly in SQLite while designing the tools (FY2024 final snapshot).
    v = analysis.within_office_variation(fiscal_year=2024, limit=1)
    assert v["items"][0]["office"] == "ORLAND PARK" and v["items"][0]["gap_pts"] > 80
    t = trends.national_trend()
    fy = {s["fiscal_year"]: s for s in t["series"]}
    assert fy[2012]["total_dispositions"] > 780_000 and fy[2022]["total_dispositions"] < 365_000
    o = analysis.outlier_report(level="judge", fiscal_year=2024, limit=5)
    assert o["total"] > 0 and all(abs(i["z_score"]) >= 2 for i in o["items"])
    p = trends.monthly_pace(fiscal_year=2026)
    assert any("flags" in x for x in p["periods"])  # the missing July/August 2026 snapshots
