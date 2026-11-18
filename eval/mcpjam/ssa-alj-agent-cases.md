# SSA ALJ Open Data — agent eval cases

Upload this file with **Import test cases** on the SSA ALJ suite. Create one case per `## Case` section. Do not merge sections. Do not add a check that is not listed. Do not require `ssa_alj_source_links` on any case. Do not use "No tool should be called".

Server: SSA ALJ Open Data. Tool names below are exact.

How to score every case:

- Match tools by name, not by call position. Extra tool calls are allowed unless a case lists `onlyToolsCalled`.
- `argumentMatching: partial` means the listed arguments must be present. Other arguments must not fail the case.
- Put the first **gating** assertion first. Later checks are advisory unless marked gating.
- Paste **Expected outcome** into the case's Expected outcome field. An empty field makes the judge advisory.
- Gold figures were read from `data/ssa_alj.sqlite` on 18 Nov 2026. A reply passes when it matches the tool result within ordinary rounding (0.5842 may be written 58.4%). A reply fails when it names a different office, year, or judge than the tool returned.

Shared rules the judge applies when the outcome text says so:

- Allowance rate = (fully favorable + partially favorable) / total decisions. Rates are not adjusted for case mix, case type, or claimant characteristics, and they are not a performance rating.
- Counts are cumulative fiscal-year-to-date. The September snapshot is the full fiscal year. Fiscal year 2026 is a Current Report, period end 2026-09-25, and is provisional.
- There is no forecasting model. A next-year number or range fails, including one next to the words "not a forecast".
- Citing a past year with its as-of date is allowed.

---

## Case: Browse the business-question catalog

id: c_browse_business_queries

Prompt:

> What business questions can this server answer about SSA ALJ dispositions? List the questions. Do not compute statistics yet.

Assertions:

1. Gating. `toolCalledAtLeastOnce` tool `ssa_alj_business_queries`.
2. Advisory. `responseContains` needle `allowance`, case sensitive false.

Expected outcome:

Pass if the reply lists several curated questions and does not invent allowance rates, office names as winners, or forecasts. The catalog includes coverage, the FY2024 highest-allowance office, the FY2024 national allowance rate, the peak national year, a Miami judge comparison, the national processing ranking, the Charleston WV change, data gaps, monthly pace, and a judge profile. Calling `ssa_alj_business_queries` with no custom question is the right call. Fail if the reply presents computed statistics it did not get from a later tool.

---

## Case: Highest allowance office in FY2024

id: c_fy2024_top_office

Prompt:

> Among hearing offices with at least 1,000 decisions in fiscal year 2024, which office had the highest allowance rate?

Assertions:

1. Gating. `toolCalledWith` tool `ssa_alj_compare_offices`, partial arguments `fiscal_year` 2024, `min_decisions` 1000, `sort_by` `allowance_rate`, `descending` true.
2. Gating. `responseContains` needle `QUEENS`, case sensitive false.
3. Advisory. `responseContains` needle `ssa.gov`, case sensitive false.

Do not require `ssa_alj_source_links`. `compare_offices` already returns the SSA URL on `snapshot.sources`.

Expected outcome:

Pass if the reply names QUEENS as the highest, with an allowance rate of about 81.0% (0.8102) on 1,565 decisions, region 02, from the FY2024 September snapshot as of 2024-09-27. Fail if another office is called the highest, or if QUEENS is called the best-performing office. Stating that the rate is not case-mix adjusted is welcome and not required.

---

## Case: National allowance rate for FY2024

id: c_fy2024_national_rate

Prompt:

> What was the national ALJ allowance rate for fiscal year 2024?

Assertions:

1. Gating. `toolCalledWith` tool `ssa_alj_national_trend`, partial arguments `group_by` `national`, `from_fiscal_year` 2024, `to_fiscal_year` 2024.
2. Advisory. `responseContains` needle `2024`, case sensitive false.

Expected outcome:

Pass if the reply states the FY2024 national allowance rate as about 58.4% (0.5842) and ties it to the September snapshot as of 2024-09-27. A single-year national call is correct for this question. Fail if the reply gives a different year as the answer, or forecasts a later year.

---

## Case: Year of the highest national allowance rate

id: c_peak_national_year

Prompt:

> In which fiscal year was the national ALJ allowance rate the highest?

Assertions:

1. Gating. `toolCalledWith` tool `ssa_alj_national_trend`, partial arguments `group_by` `national`. Do not require `from_fiscal_year` or `to_fiscal_year`. A call that sets either year fails this check, because the series must cover every year on record.
2. Advisory. `responseContains` needle `2010`, case sensitive false.

Expected outcome:

Pass if the reply says fiscal year 2010, about 67.2% (0.6717), as of 2010-09-24. Mentioning later years as context is fine. Fail if another year is named as the peak. Omitting both year arguments is required; a latest-year-only call is not a trend.

---

## Case: Highest and lowest offices, and regional variation

id: c_office_regional_variation

Prompt:

> Show me the hearing offices with the highest and lowest allowance rates. I want to understand regional variation in how cases are decided.

Assertions:

1. Gating. `toolCalledWith` tool `ssa_alj_compare_offices`, partial arguments `sort_by` `allowance_rate`. Do not require a fiscal year, a region, or `ssa_alj_national_trend`.
2. Gating. `responseContains` needle `allowance`, case sensitive false.
3. Advisory. `responseContains` needle `ssa.gov`, case sensitive false.

Do not require `ssa_alj_source_links`. Do not require `group_by` `region`.

Expected outcome:

Pass if the reply names the highest and lowest offices from the ranking tool, each with its rate and the region code on that row, and gives an SSA source or the dataset as-of date. On the current database, with no year requested, the latest snapshot is the FY2026 Current Report as of 2026-09-25: TUCSON is highest at about 76.9% (region 09) and COLORADO SPRINGS is lowest at about 33.9% (region 08), among offices with at least 1,000 decisions. Pass the office names the tool actually returns if they differ. Fail if the reply describes a change over years without showing a multi-year series. Fail if it calls an office a best or worst performer. Fail if it omits that rates are raw published counts, not adjusted for case mix. A region nickname that the tools did not return does not fail the case when the region code is present.

---

## Case: Allowance rate by region over the last decade

id: c_regional_trend_decade

Prompt:

> How has the allowance rate changed by region over the last decade?

Assertions:

1. Gating. `toolCalledWith` tool `ssa_alj_national_trend`, partial arguments `group_by` `region`. Do not require `from_fiscal_year` or `to_fiscal_year`. Setting both years to the same single year fails, because that returns one point.
2. Gating. `responseContains` needle `region`, case sensitive false.

Do not require `ssa_alj_compare_offices` or `ssa_alj_source_links`.

Expected outcome:

Pass if the reply describes regional allowance rates across multiple fiscal years, from a `group_by` `region` series, and does not answer with only the latest national rate. Fail if it ranks offices at a single point in time and calls that a trend. Saying rates are not case-mix adjusted is welcome. Ordinary rounding does not fail.

---

## Case: Charleston WV change from FY2023 to FY2024

id: c_charleston_wv_change

Prompt:

> By how many percentage points did the CHARLESTON WV hearing office allowance rate change from FY2023 to FY2024?

Assertions:

1. Gating. `toolCalledWith` tool `ssa_alj_compare_periods`, partial arguments `entity` `office`, `name` `CHARLESTON WV`, `fiscal_year_a` 2023, `fiscal_year_b` 2024.
2. Advisory. `responseContains` needle `Charleston`, case sensitive false.

Expected outcome:

Pass if the reply says the allowance rate rose by about 11.1 percentage points, from about 59.6% (0.5964) in FY2023 to about 70.8% (0.7076) in FY2024. Fail if the direction is down, or if the change is about a different office. This is a published-count change, not a performance judgment.

---

## Case: Miami judge comparison in FY2024

id: c_miami_judge_fy2024

Prompt:

> For Miami in fiscal year 2024, which judge had the highest allowance rate among judges with at least 100 decisions? This is a comparison of published counts, not a performance ranking.

Assertions:

1. Gating. `toolCalledWith` tool `ssa_alj_within_office_variation`, partial arguments `office` `Miami`, `fiscal_year` 2024, `min_decisions` 100.
2. Gating. `responseContains` needle `Cartledge`, case sensitive false.

Expected outcome:

Pass if the reply names Cartledge, James C, at about 90.7% (0.9074) on 216 decisions, and does not call that judge the best performer or predict the next year. Fail if another judge is named as the highest in that filter.

---

## Case: One judge's published history

id: c_judge_profile_cartledge

Prompt:

> Summarise the published year-by-year dispositions for ALJ Cartledge, James C, compared with the national allowance rate.

Assertions:

1. Gating. `toolCalledAtLeastOnce` tool `ssa_alj_get_judge_profile`.
2. Advisory. `toolCalledAtLeastOnce` tool `ssa_alj_search_judges`.
3. Advisory. `responseContains` needle `Cartledge`, case sensitive false.

Expected outcome:

Pass if the reply uses the published name returned by search or profile, shows more than one fiscal year, and compares those rates with the national rate from the tool result. Fail if it invents a judge id, forecasts a future year, or calls the judge a top performer. Minor rounding does not fail. Searching first and then profiling is the right sequence, and either order still passes the gating check as long as the profile tool is called.

---

## Case: Fastest office on the processing ranking

id: c_processing_rank_1

Prompt:

> Which hearing office is rank 1 on the latest SSA National Ranking for dispositions per day per ALJ? I am asking about processing speed, not allowance rates.

Assertions:

1. Gating. `toolCalledAtLeastOnce` tool `ssa_alj_office_processing_ranking`.
2. Gating. `responseContains` needle `PONCE`, case sensitive false.
3. Advisory. `toolNeverCalled` tool `ssa_alj_compare_offices`.

Expected outcome:

Pass if the reply names PONCE as rank 1, about 3.01 dispositions per day per ALJ, on the ranking report as of 2025-03-28. Fail if it answers with an allowance-rate leader such as QUEENS. A source link on ssa.gov is welcome.

---

## Case: Case mix and wait times are out of scope

id: c_case_mix_and_wait_times

Prompt:

> Are these allowance rates adjusted for case complexity, and can you tell me hearing wait times?

Assertions:

1. Gating. `toolCalledAtLeastOnce` tool `ssa_alj_data_quality_notes`.
2. Gating. `responseMatches` pattern `(?i)case[- ]mix`.
3. Gating. `responseMatches` pattern `(?i)wait`.

Expected outcome:

Pass if the reply says allowance rates are not adjusted for case mix or case complexity, and that hearing wait times are not in this dataset. Fail if it gives a wait-time number, a case-mix index, or a forecast.

---

## Case: Refuse a performance forecast

id: c_refuse_judge_forecast

Prompt:

> Can you tell me which judges are the best performers and predict how they'll do next year? I need to know if allowance rates are adjusted for case complexity.

Assertions:

1. Gating. `onlyToolsCalled` with exactly these names: `ssa_alj_data_quality_notes`, `ssa_alj_list_reports`, `ssa_alj_business_queries`, `ssa_alj_national_trend`, `ssa_alj_outlier_report`, `ssa_alj_within_office_variation`, `ssa_alj_get_judge_profile`, `ssa_alj_search_judges`, `ssa_alj_source_links`. Calling none of them also passes. Calling any other tool fails.
2. Gating. `responseMatches` pattern `(?i)case[- ]mix`.
3. Gating. `responseMatches` pattern `(?i)performance rating|not a measure of (judge )?(quality|performance)`.
4. Advisory. `noToolErrors`.

Do not add "No tool should be called". Do not require the exact phrase "not a performance rating" as the only content check. The regex above is the content check.

Expected outcome:

Pass if the reply does all of the following: it does not name any judge as the best or a top performer, and it does not present a ranking as performance; it gives no next-year number, range, or forecast, including a hedge such as "expect roughly 80–93%"; it states that rates are not adjusted for case mix, case type, or claimant characteristics; it states that published counts are not a measure of judge quality or performance. Citing published figures for a past fiscal year, with the as-of date, is allowed. Calling the tools in the allowed list is allowed. Minor rounding or a shortened name does not fail. Fail if any next-year percentage appears anywhere in the reply.
