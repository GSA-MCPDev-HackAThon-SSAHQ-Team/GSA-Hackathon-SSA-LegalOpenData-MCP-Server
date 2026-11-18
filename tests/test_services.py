"""Service-level tests against the synthetic DB."""

from __future__ import annotations

from ssa_alj_mcp.services import judges, offices, reports


def test_list_reports_uses_final_snapshot_per_year(db_path):
    r = reports.list_reports()
    assert [s["fiscal_year"] for s in r["fiscal_year_final_snapshots"]] == [2023, 2024]
    assert r["fiscal_year_final_snapshots"][0]["period_end"] == "2023-09-29"
    assert len(reports.list_reports(2023)["fiscal_year_snapshots"]) == 2


def test_search_judges_groups_name_variants(db_path):
    r = judges.search_judges("baker")
    assert r["total"] == 1
    assert r["items"][0]["name_variants"] == ["Baker, Bob", "Baker, Bob."]


def test_search_judges_word_order_and_filters(db_path):
    assert judges.search_judges("ann adams")["total"] == 1
    assert judges.search_judges("adams", fiscal_year=2024)["total"] == 1
    assert judges.search_judges("clark", fiscal_year=2023)["total"] == 1
    assert judges.search_judges("baker", fiscal_year=2023)["total"] == 0
    assert judges.search_judges("zzz")["total"] == 0


def test_judge_profile_math_and_final_snapshot_only(db_path):
    r = judges.get_judge_profile("Adams, Ann")
    fy23 = next(x for x in r["fiscal_years"] if x["fiscal_year"] == 2023)
    assert fy23["total_decisions"] == 100  # June snapshot (10 decisions) must not be added
    assert fy23["allowance_rate"] == 0.8
    assert fy23["other_dispositions"] == 20
    assert fy23["national_allowance_rate"] == round((80 + 40) / (100 + 100), 4)


def test_judge_profile_by_office_when_fiscal_year(db_path):
    r = judges.get_judge_profile("adams", fiscal_year=2024)
    assert [o["office"] for o in r["by_office"]] == ["MIAMI, FL"]


def test_judge_profile_errors(db_path):
    assert "error" in judges.get_judge_profile("nobody")
    assert "error" not in judges.get_judge_profile("bob")  # Baker variants collapse into one judge


def test_compare_offices_ranks_by_allowance_rate(db_path):
    r = offices.compare_offices(fiscal_year=2024, sort_by="allowance_rate")
    assert [i["office"] for i in r["items"]] == ["MIAMI, FL", "ATLANTA DOWNTOWN", "ATLANTA NORTH"]
    assert r["snapshot"]["period_end"] == "2024-09-27"
    r2 = offices.compare_offices(fiscal_year=2024, min_decisions=50)
    assert {i["office"] for i in r2["items"]} == {"MIAMI, FL", "ATLANTA NORTH"}


def test_compare_offices_validation(db_path):
    assert "error" in offices.compare_offices(sort_by="bogus")
    assert "error" in offices.compare_offices(fiscal_year=1999)
    assert "error" in offices.compare_offices(as_of="not-a-date")
    assert offices.compare_offices(as_of="2023-06-30")["snapshot"]["report"] == "June"


def test_office_profile_merges_name_variants(db_path):
    r = offices.get_office_profile("miami")
    assert r["office"] == "MIAMI"
    assert r["published_names_combined"] == ["MIAMI OHO", "MIAMI, FL"]
    assert [y["fiscal_year"] for y in r["fiscal_years"]] == [2023, 2024]


def test_office_profile_ambiguous_and_unknown(db_path):
    amb = offices.get_office_profile("atlanta")
    assert "candidates" in amb and len(amb["candidates"]) == 2
    assert "error" in offices.get_office_profile("nowhere")
    assert "error" not in offices.get_office_profile("atlanta north", fiscal_year=2024)


def test_processing_ranking(db_path):
    r = offices.office_processing_ranking()
    assert r["items"][0]["office"] == "MIAMI OHO"
    assert r["snapshot"]["period_end"] == "2024-03-29"
    assert "error" in offices.office_processing_ranking(period_end="2000-01-01")


def test_missing_database_returns_error_payload(tmp_path, monkeypatch):
    from ssa_alj_mcp.config import settings

    monkeypatch.setattr(settings, "ssa_alj_db_path", tmp_path / "missing.sqlite")
    assert "error" in reports.list_reports()
