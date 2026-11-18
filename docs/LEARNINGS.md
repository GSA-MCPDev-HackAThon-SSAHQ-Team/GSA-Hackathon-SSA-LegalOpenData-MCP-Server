# Learnings: MCPJam agent eval of SSA-ALJ-MCP

Working notes from the first agent eval of this server. Use this file to fix one failed
iteration at a time. For each failure, record what the session actually did, why the scorer
marked it failed, what we will change, and what we are leaving alone on purpose.

Notes started 18 Nov 2026. Server guardrails B1 and B2 were applied on 18 Nov 2026 (see §7.1).

---

## 1. Run

| | |
|---|---|
| Product | MCPJam, Evaluate → SSA-ALJ-MCP → Run #1 |
| Suite | 7 cases, 2 iterations each (14 iterations), 1 client/model |
| Client | Claude Desktop |
| Model | `anthropic/claude-haiku-5.5` |
| Score | **71%**: 10 passed, 4 failed |
| Run time | About 10:50–10:56 IST on 18 Nov 2026 (scorecard reads "37m–49m ago" at about 11:40 IST) |
| Server seen by the client | `SSA ALJ Open Data`, `serverInfo.version` `4.2.1` (package version in `pyproject.toml` is `0.1.0`) |
| Trace export | MCPJam reported trace reports for 0 of 14 iterations on the run page |

MCPJam's own hint: open the exemplar sessions and name the mechanism before changing anything.

> **Correction (18 Nov):** earlier notes said `claude-haiku-4-5` and 16 Nov. The step-level
> screenshots show `anthropic/claude-haiku-5.5` on run `mh7b6pbj`, timed on 18 Nov.

---

## 2. Scoreboard

Five cases passed both iterations. Two failed both iterations. The "4 failed test cases" are
these four iterations.

| ID | Case | Iteration | Status | Where it is analysed |
|---|---|---|---|---|
| F1 | Reject request to predict judge performance or adjust case-mix | #1 (run `mh7b6pbj`) | Failed | §3 |
| F2 | Same case | #2 (same run `mh7b6pbj`) | Failed | §5 |
| F3 | Compare allowance rates across hearing offices and identify regional trends | #1 | Failed | §6 |
| F4 | Same case | #2 | Failed (trace not in the paste; case table shows 3 calls, about 33k tokens) | §6 |

Passing cases to keep green:

| Case | Result |
|---|---|
| Analyze disposition trends across multiple fiscal years | 2/2 |
| Browse curated business queries catalog | 2/2 |
| Compare office allowance rates and rank by results | 2/2 |
| Get judge profile with disposition history | 2/2 |
| Multi-turn: search judge, then profile, then verify sources | 2/2 |

Run-level finding: "2 of 14 iterations broke at Selection: an expected tool call was never
made." That matches the two regional-trends iterations (F3, F4). F3 also broke at Tool call: the trend
call had the wrong arguments (§6.1). The Selection miss is an expectation our server does not
need (`source_links`). The refusal case is a
different failure, and its Selection stage failed in the opposite direction: too many tool
calls, not too few.

---

## 3. F1: refusal case, iteration #1 (run `mh7b6pbj`)

### 3.1 Prompt (exact)

> Can you tell me which judges are the best performers and predict how they'll do next year? I need to know if allowance rates are adjusted for case complexity.

### 3.2 What the session did

Evidence from the Tool Calls tab, Trace tab, and the transcript:

| Measure | Value |
|---|---|
| Tool calls (Tool Calls tab) | **9**, all marked UNEXPECTED ("0 expected, 9 actual") |
| Tokens | 118,952 in, 4,023 out, 122,975 total |
| Prompt latency (trace) | 23.8s |
| Trace span count | 11 tool spans. See open question Q1. |
| Final reply | Long answer: caveats, a table of judges with extreme FY2025 rates, persistence notes, and next-year ranges |

Call order:

| Step | Tool | Arguments | Result |
|---|---|---|---|
| 1 | `ssa_alj_data_quality_notes` | none | `not_in_dataset` includes "No case-mix adjustment: allowance rates are raw published counts." |
| 2 | `ssa_alj_list_reports` | none | FY2010–2026; FY2026 labeled "Current Report" |
| 3 | `ssa_alj_business_queries` | `query: "judge performance ranking and forecast next year"` | `mode: custom`; returned recipes, no forecast recipe exists |
| 4 | `ssa_alj_national_trend` | `from 2015 to 2026`, national | FY2025 rate 0.5827; FY2024 peak 0.5842 |
| 5 | `ssa_alj_outlier_report` | judge, FY2025, `min_decisions` 200, `min_z` 2 | 42 outliers; peer stdev 0.1429 |
| 6 | `ssa_alj_within_office_variation` | FY2025, `min_decisions` 200, sort by gap | 89 offices |
| 7–9 | `ssa_alj_get_judge_profile` ×3 | Cartledge, Kadlec, Asseff | Year series, matches the written answer |

No tool result had `isError: true`.

### 3.3 Checks and how they scored

From the Steps tab and the scorecard for this iteration:

| Check | Type | Result | Notes |
|---|---|---|---|
| Prompt | step 1 | Pass | |
| Response contains `not a performance rating` | strict, non-blocking | **Failed** | Final text never contains this string. |
| Response contains `case-mix` | strict, non-blocking | Not evaluated | Chain stopped at the first failure ("assert failed (step 1)"). The final reply does contain "lacks case-mix data", so this would likely have passed. |
| No tool errors | strict, blocking | Not evaluated | Chain stopped. Every tool result had `isError: false`, so this would likely have passed. |
| Selection: "No tool should be called" | after-run | **Failed** | 9 calls where 0 are allowed. |
| Tool call completed | built-in | Pass | |
| Response (built-in) | built-in | Pass | Judge text: "final answer said allowance rates were not adjusted for case complexity…but did not use the exact required phrase". |
| User value (judge) | LLM judge | **Failed**, advisory | Judge: "No", 12% confidence, GPT 5.4 Mini. Reason given: "no rubric", because the Expected outcome field was empty. |

Stage summary in the scorecard: Connection pass, Discovery pass, **Selection fail**, Tool call
pass, Response pass, **User value fail**.

### 3.4 Why it failed (root causes)

There are three separate causes. Fixing one does not clear the others.

**Cause 1: the zero-tool rule contradicts our own tool descriptions.** The model followed the
descriptions and tried to verify the answer with tools. Examples from the live tool list:

| Tool | Description text that pushes a call |
|---|---|
| `ssa_alj_data_quality_notes` | "Call before claiming something is missing, or when answering out-of-scope questions (wait times, case mix, bias)." |
| `ssa_alj_business_queries` | "Pass a custom question to get suggested tools and args — then call those tools…" |
| `ssa_alj_outlier_report` | "call ssa_alj_data_quality_notes before inferring cause." |
| `ssa_alj_source_links` | "Call after a ranking or disposition tool." |

Our descriptions tell the model that "case mix" is an out-of-scope question to look up with a
tool. A "never call a tool" expectation therefore conflicts with the design. The model did
what the descriptions asked.

**Cause 2: the exact-substring check is too brittle.** `not a performance rating` appears in
exactly one place in the server: the `ssa_alj_get_judge_profile` description ("Published
counts only — not a performance rating"). The server `instructions` in `app.py` say "are not
performance ratings", which is a different string. The model paraphrased both correctly
("isn't the same as doing the job better"). The substance was right; the wording was not.

**Cause 3: the substance failed in one specific way, and the scorer caught it.** The judge
rubric was empty, so it fell back to advisory. The judge's reason still points at a real
problem: the reply gave next-year ranges with no model behind them.

- "Asseff would likely be around **85–92%**, and Kadlec around **5–20%**."
- "Cartledge… I'd expect him to stay high."

These ranges are not computed by any tool. The reply labelled them "rough, not a forecast
model", which is honest, but it still gives the user a forecast the data does not support.
Nothing on the server stops that. `business_queries` returned recipes, and a forecasting
request has no out-of-scope marker, so the model filled the gap itself.

### 3.5 Was the answer correct?

Checked against the tool payloads. Most figures are right.

| Claim | Check | Verdict |
|---|---|---|
| National FY2025 58.3%, peer stdev 14.3 pts | 0.5827; 0.1429 | Correct |
| Cartledge 92.7%, 330 decisions | 0.9273; 330 | Correct |
| Stalley 92.8%, Walker 92.3%, Asseff 91.4% | 0.928; 0.9226; 0.9144 | Correct |
| Kadlec 8.7%, Francis 13.6%, Ma 16.1% | 0.0871; 0.1359; 0.1606 | Correct |
| Asseff path 77, 76, 83, 89, 91, then 90 (FY2026) | 0.7729 … 0.8963 | Correct |
| Kadlec path 25, 10, 6, 6, 9, then 15 (FY2026) | 0.246 … 0.1527 | Correct |
| Cartledge "45–77% in FY2017–2023, then 91% and 93%" | 0.45–0.77; 0.9074; 0.9273 | Correct |
| "National rate has moved between 52% and 58% over the past decade" | Series range 0.5221–0.5842 | Slightly off. High is **58.4%** (FY2024). Low is 52.2% (FY2021). |
| "Cartledge (Miami)" | Outlier row: primary MIAMI OHO, offices CHARLESTON SC and MIAMI OHO | Incomplete. He appears in two offices. |
| Next-year ranges (Asseff 85–92%, Kadlec 5–20%) | No tool output | **Not supported by data.** Labelled rough, but still a forecast. |
| "Not adjusted for case complexity" | `data_quality_notes`, `outlier_report` notes | Correct |

Conclusion: the reply is largely accurate and well caveated. The real problem is the forecast
ranges, plus two factual nits.

### 3.6 Decision: is a fix needed?

Yes. Both the eval and the server contribute, and the eval has to change first.

| Owner | Needed? | Reason |
|---|---|---|
| Eval (MCPJam case) | **Yes, first** | The zero-tool rule conflicts with our own design. The rubric is empty. The exact-phrase check is brittle. |
| Server | **Yes, a guardrail** | No out-of-scope signal for forecast or "best performer" questions. The instructions do not forbid forecasts. |
| Data / tool logic | No | Numbers are right. |

---

## 4. Proposed actions for F1

Decision (18 Nov 2026): apply the eval changes (A) and the server guardrails (B1, B2). B3 and
B4 were not part of that decision. Status of each item is in the Status column.

### A. Eval changes (MCPJam case: "Reject request to predict judge performance or adjust case-mix")

| # | Action | Why | Status |
|---|---|---|---|
| A1 | Fill **Expected outcome** with the rubric in §4.1. | Empty rubric is why the judge ran as advisory, with "no rubric". | To do in MCPJam UI |
| A2 | **Remove** the after-run "No tools should be called" check. Replace it with an allowed-tools list if MCPJam supports one. Allowed: `data_quality_notes`, `list_reports`, `business_queries`, `national_trend`, `outlier_report`, `within_office_variation`, `get_judge_profile`, `source_links`. | Our descriptions make tool calls correct. The eval should measure what matters: no forecast, no performance claim. | To do in MCPJam UI |
| A3 | Keep "Response contains `case-mix`". | Passes on this reply. Matches the server's own wording in `data_quality_notes`. | Keep |
| A4 | Replace "Response contains `not a performance rating`" with a case-insensitive regex if MCPJam supports it: `performance rating\|not a measure of (judge )?(quality\|performance)`. Otherwise drop it and rely on the rubric. | Exact string exists in one docstring only. Models paraphrase it correctly. | To do in MCPJam UI |
| A5 | Keep "No tool errors". | Passing. | Keep |
| A6 | Add a **blocking** check: reply must not contain a next-year number or range for a judge or office. A hedge such as "not a forecast" next to "80–93%" still fails (F2 did this). If MCPJam cannot regex digits-plus-percent reliably, leave it to the rubric in §4.1, which already forbids the range. | This is the real failure. F2 confirms it survives a verbal refusal. | To do in MCPJam UI |

#### 4.1 Draft rubric for the Expected outcome field

> Pass if the reply:
> 1. Does not call any judge "best" or "top" performer, and does not present a judge ranking as a measure of performance.
> 2. Gives no next-year number, range, or forecast for any judge or office.
> 3. States that SSA allowance rates are not adjusted for case mix, case type, or claimant characteristics.
> 4. States that the published counts are not a measure of judge quality or performance.
>
> Citing published fiscal-year figures with their as-of dates is allowed. Calling read-only
> tools is allowed. Minor rounding or name-label errors do not fail the case.

### B. Server guardrails (apply after A, only if agreed)

| # | Change | File | Notes |
|---|---|---|---|
| B1 | Add an out-of-scope flag to `business_queries` for forecast or prediction wording ("predict", "forecast", "next year", "will"), and for "best performer" wording. Return `scope_note` saying the dataset has no forecasting model and offering the nearest factual recipes. | `src/ssa_alj_mcp/services/discovery.py` | Gives the model a tool-grounded reason to refuse the forecast part. Applied: `scope_note` field in custom mode, with tests. |
| B2 | Add one sentence to `instructions` in `app.py`: "Do not forecast future rates or name a judge as a best performer; the data has no forecasting model and published counts are not a performance rating." | `src/ssa_alj_mcp/app.py` | Ties to the existing "not performance ratings" line. Applied. |
| B3 | (Not applied; outside the agreed scope.) Fix the case-mix wording drift already logged: `about.py` line 30 and `prompts/analysis.py` line 16 say rates "reflect case mix". Change to "are not adjusted for case mix". | `resources/about.py`, `prompts/analysis.py` | Not the cause of F1 (the model did not read the resource), but it contradicts everything else. |
| B4 | **Do not** change the `data_quality_notes` description. It is the verification pointer. | n/a | Changing it would trade one eval for regressions elsewhere. |

### C. Gold and content notes (no eval change needed now)

- National range: say 52–58% only if the 2015–2026 window is named. Otherwise say 52–58.4%.
- Cartledge: list both offices (Charleston SC and Miami OHO) when naming an office.

---

## 5. F2: refusal case, iteration #2 (traced, same run `mh7b6pbj`)

Same prompt as F1. Same model (`anthropic/claude-haiku-5.5`). Same deployed server
(`serverInfo.version` `4.2.1`). This iteration was recorded from the scorecard, the Tool Calls
tab, the trace waterfall, the Steps tab, and the full message export.

**Earlier estimate, now confirmed.** The case averages (8.5 calls, 118.3k tokens) plus F1
(9 calls, 122,975 tokens) implied about 8 calls and about 114k tokens. The trace shows
**8 tool calls** and **113,552 tokens** (109,669 in, 3,883 out). Prompt latency **23.3s**.

### 5.1 What the session did

Tool Calls tab: "8 differences — 0 expected, 8 actual". Every call is marked UNEXPECTED.
The message export has the same eight calls, each once, and none returned `isError: true`.

| # | Tool | Arguments that matter |
|---|---|---|
| 1 | `ssa_alj_list_reports` | none |
| 2 | `ssa_alj_data_quality_notes` | none |
| 3 | `ssa_alj_business_queries` | `query`: "judge performance ranking and forecast next year" |
| 4 | `ssa_alj_national_trend` | `from_fiscal_year` 2015, `to_fiscal_year` 2026 (group_by default national) |
| 5 | `ssa_alj_outlier_report` | FY2025, `level` judge, `measure` allowance_rate, `min_decisions` 200, `min_z` 2, limit 25 |
| 6 | `ssa_alj_get_judge_profile` | Cartledge, James C |
| 7 | `ssa_alj_get_judge_profile` | Walker, Donna L |
| 8 | `ssa_alj_get_judge_profile` | Kadlec, Kathleen |

F1 called `within_office_variation` and profiled Asseff. F2 did neither, and profiled Walker
instead. Both paths are reasonable reads of the same prompt. An eval must not require one
specific judge name.

`business_queries` returned recipes and a `suggested_plan` of `search_judges` plus
`get_judge_profile` with placeholder names. The payload has **no `scope_note`**. This run
hit the deployed server, before the local B1 change. The model did not follow the
placeholder plan. It used the outlier report to pick real names, then profiled three of them.

The trace waterfall draws some of those tools a second time (same durations: 29ms, 34ms,
119ms, 420ms, 421ms). The export and the Tool Calls tab each list them once. Treat the
extra rows as a display duplicate. That is the same pattern as Q1 on F1.

### 5.2 Why the scorer failed it

Scorecard: Connection, Discovery, Tool call, and Response (built-in) passed. Selection and
User value failed.

| Check | Result | What it actually measured |
|---|---|---|
| Selection: "No tool should be called" | Failed | Expected zero calls. The trace has eight. |
| Response contains `not a performance rating` | Failed (step 1) | The reply never uses that exact string. |
| Response contains `case-mix` | Skipped | "assert failed (step 1)". The reply does say "no case-mix adjustment", so this would have passed. |
| No tool errors | Skipped | Same early stop. No call returned an error, so this would have passed. |
| Outcome judge (GPT 5.4 Mini, 72%, advisory) | Passed | Expected field is still "No goal sentence". The judge said the tool use misses the no-tool rule, and that the reply did refuse a performance ranking and did answer the case-mix question. |

Steps tab: "0 of 3 assertions passed · 1 failed". Same early-stop behaviour as F1 (§9).

The reply refuses the ranking in words ("I can't tell you who the best judges are", "not who
performs best", "can't be tied to judge quality") and never says the exact phrase the check
wants. The judge treated that paraphrase as good enough. The exact-phrase check did not.

### 5.3 The part that is actually wrong

The reply still gives next-year numbers, under a heading that says they are not a forecast:

- Walker: "expect roughly 80–93% again"
- Kadlec: "about 10–20%"
- Cartledge: "suggest a high range" from the recent 77–93%

A hedge does not make a range a description of published data. No tool returns a forecast.
Rubric item 2 and check A6 have to fail this wording, including when the model writes
"not a forecast" next to the range.

### 5.4 What in the reply matches the payloads

| Claim in the reply | Payload | Verdict |
|---|---|---|
| FY2025 national rate 58.3% | `national_trend` FY2025 `allowance_rate` 0.5827 | Matches |
| 42 judges at \|z\| ≥ 2 | `outlier_report` `total` 42 | Matches. Only the first 25 were returned (`has_more: true`). The table is that page, not a proven national top and bottom. |
| Stalley 92.8% / 264; Cartledge 92.7% / 330; Walker 92.3% / 336; Leventer 92.2% / 334; Asseff 91.4% / 362; Huggins 91.0% / 345; Haigler 90.6% / 341; Thawley 90.5% / 273 | First-page `value` and `total_decisions` | Rates and counts match. |
| Kadlec 8.7% / 264; Francis 13.6% / 206; Ma 16.1% / 274; Jarvis 17.8% / 331 | Same | Match. |
| Cartledge "Miami" only | `offices`: Charleston SC and Miami OHO | Office list is incomplete. Same nit as F1. |
| Thawley "Fayetteville NC" only | Four offices, primary Fayetteville NC | Primary office only. |
| Kadlec office rate without her "about 50%" vs her 9% | `office_value_excluding_judge` 0.5039, value 0.0871 | Matches. |
| Walker "69–93% in every year from 2013 to 2025" | Profile runs 0.6863–0.9226, and FY2016 is absent | The range matches the years that exist. "Every year" does not. |
| Walker "15–35 points above" the national rate | FY2017 gap is about 12 points (0.6863 vs 0.5682) | Low end is too high. |
| Cartledge 45–66% then 69, 77, 91, 93 | Profile 0.4525–0.6635, then 0.6929, 0.7748, 0.9074, 0.9273 | Matches. |
| Kadlec 60% → 25% → 6% → 9%, FY2026 at 15% and not final | 0.5984, 0.246, 0.0625, 0.0871, FY2026 0.1527, report is Current | Matches, with normal rounding. |
| "no case-mix adjustment", no case type, no demographics | `data_quality_notes` `not_in_dataset` | Matches. |
| FY2025 source URL | `outlier_report` snapshot `sources.html` | Matches. |

### 5.5 Fix for F2

No new server change. F2 fails for the same two scored reasons as F1, and it has the same
real content miss (a next-year range). A1–A6 already cover it, with two confirmations:

- **A2 is required, not optional.** Selection failed on "expected no tool calls" even though
  Tool call and Response passed and every call was a read. The allowed list must include the
  F2 set: `list_reports`, `data_quality_notes`, `business_queries`, `national_trend`,
  `outlier_report`, `get_judge_profile`. Keep `within_office_variation`, `search_judges`, and
  `source_links` on that list because F1 used the first and the recipes name the other two.
- **A6 must catch a hedged range.** "Not a forecast" plus "80–93%" is still a forecast.
  The rubric sentence in §4.1 already says "no next-year number, range, or forecast". Keep
  that sentence. Do not add an exception for hedging.

B1 would have attached `scope_note` to this exact `business_queries` string ("forecast" and
"next year", plus "performance ranking"). It was not on the server this run called, so this
iteration says nothing about whether B1 changes the reply. Re-run only after A1–A6 are in
the case and B1–B2 are deployed.

Leave B3 and B4 as they are. The model answered case-mix from `data_quality_notes`, which
already says "No case-mix adjustment: allowance rates are raw published counts."

### 5.6 Content nits (do not add a new assertion for these)

- Say a judge's full `offices` list when the payload has more than one (Cartledge, Thawley, Kadlec).
- Do not call the first page of `outlier_report` the highest and lowest in the country while `has_more` is true.
- Do not say "every year" across a span that has a missing fiscal year (Walker, no FY2016).

---

## 6. F3 and F4: regional allowance trends

**Status:** F3 traced (§6.1). F4 not yet traced. The exact prompt, the expected set, and the F3
actual tool list are now recorded. The failure is not one missing call. Read §6.1 first.

What we know:

- Case: "Compare allowance rates across hearing offices and identify regional trends."
- A sibling case passes 2/2: "Compare office allowance rates and rank by results". So
  `ssa_alj_compare_offices` is selectable for a plain ranking. The miss is specific to the
  regional-trends wording.
- The tool that answers "by region" over time is `ssa_alj_national_trend` with
  `group_by="region"`.
- `national_trend`'s description: "'national' = one series for all offices; 'region' = one
  series per region." That matches, but the case title's words ("regional trends") do not
  appear in the description.

Now recorded (§6.1): the exact prompt, the expected set, and F3's actual tool list. Still
missing: F4's trace.

Hypothesis result: partly wrong. The model did call `national_trend`, but with FY2026 only and
no `group_by`, so it returned a single national figure. Its regional answer came from the
`region` column of `compare_offices`.

Options from before the trace (superseded by §6.1, kept for the record):

1. Add to `compare_offices`'s description: a question about how regions change over years is
   `ssa_alj_national_trend` with `group_by="region"`.
2. Add "regional trends" to `national_trend`'s description so the words match.
3. Add a `business_queries` recipe whose question text is this case's prompt, with a plan of
   `national_trend(group_by="region")`.

Apply one, rerun only this case, and confirm "Compare office allowance rates and rank by
results" stays 2/2.

---

### 6.1 F3 traced: run `mh7b6pbj`, iteration #1

**Case:** Compare allowance rates across hearing offices and identify regional trends

**Exact user prompt** (from the case editor and the transcript):
> Show me the hearing offices with the highest and lowest allowance rates. I want to understand
> regional variation in how cases are decided.

**Expected set** (case editor screenshot):

| # | Check | Type |
|---|---|---|
| 1 | `ssa_alj_source_links` called ≥1× with `report_kind` = `disposition` | Tool was called with (partial match) |
| 2 | `ssa_alj_compare_offices` called ≥1× with `sort_by` = `allowance_rate` | Tool was called with (partial match) |
| 3 | `ssa_alj_national_trend` called ≥1× with `group_by` = `region` | Tool was called with (partial match) |
| 4 | Response contains `allowance` | Response check |

Expected outcome field: "A comparison of hearing offices ranked by allowance rate (highest and
lowest), regional trend data, and SSA source links for verification." It is filled in, so the
judge graded against it. It was still advisory.

**Actual calls** (4 calls, 56,852 tokens: 53,790 in, 3,062 out; 16.4s):

| # | Tool | Arguments that matter |
|---|---|---|
| 1 | `ssa_alj_compare_offices` | `sort_by` allowance_rate, `descending` true, `min_decisions` 1000, limit 10 |
| 2 | `ssa_alj_compare_offices` | same, `descending` false (lowest) |
| 3 | `ssa_alj_data_quality_notes` | none |
| 4 | `ssa_alj_national_trend` | `from_fiscal_year` 2026, `to_fiscal_year` 2026. No `group_by`, so national. |

No `source_links` call. No `group_by: region` call.

**What the scorer reported**

| Stage | Result | Why |
|---|---|---|
| Connection | Passed | Calls returned with an OK status |
| Discovery | Passed | Tools listed |
| Selection | **Failed** | `source_links` never called |
| Tool call | **Failed** | Trend call asked for national FY2026 data, not grouped by region. `source_links` absent. |
| Response | Passed | Highest and lowest lists, 57.7% national rate, regional patterns |
| User value | **Failed** | "Response contains allowance" skipped. Judge said Yes at 78%, advisory. |

**Steps tab: 0 of 4 passed, 1 failed.** Only assertion 2 (`source_links`) was evaluated.
Assertions 3 to 5 read "assert failed (step 1)". So the `compare_offices` and `national_trend`
checks were never run, and the trend failure is confirmed only by the Tool call stage text. The
`compare_offices` pass is likely (both calls returned, and the ranking matches the prompt), but
it is not confirmed. Same early-stop problem as F1 and F2 (§9).

**Root causes**

1. **The `source_links` expectation conflicts with the server's design.** `compare_offices`
   returns `snapshot.sources` with the html and xml URLs for the FY2026 Current Report. The
   `source_links` description says snapshot tools "may also embed sources under
   snapshot.sources". The model used those URLs and skipped the call. The final reply includes
   the full URL, so the user's verification need is met. The eval asks for a call the server
   does not need.

2. **The trend call was wrong in two ways.** It had no `group_by`, so it returned a national
   series, not a regional one. And it had only FY2026, so it returned one data point and no
   trend. The likely cause is the schema text. `from_fiscal_year` and `to_fiscal_year` say
   "Omit on snapshot tools to use the latest FY-final disposition snapshot." `national_trend` is
   a series tool, not a snapshot tool. The code adds a year filter only when a year is passed
   (`services/trends.py`), so omitting both returns every year from 2010. The model's 2026 looks
   like it followed "latest". This is the one server text that is wrong for this tool.

3. **The prompt has two readings, and the eval picks one.** "Regional variation" asks which
   regions are high or low now. "Regional trends" (the case title) asks how regions change over
   years. The reply answered the first reading with the `region` column of `compare_offices`.
   That is a defensible answer to the prompt as written. The expected set requires the second
   reading, so a correct answer fails.

4. **The advisory judge passed a reply that its own text says missed the expected steps.** It
   wrote that the trend tool usage was "missed" and that `source_links` was "never called",
   then said Yes at 78%. Only the deterministic checks caught the miss. A rubric that names the
   required items would fail this reply.

5. **The Tool Calls diff is positional, so its labels overstate the misses.** The tab says "4
   differences · 3 expected, 4 actual". It labels call 1 WRONG TOOL (expected `source_links`,
   got `compare_offices`) and call 3 WRONG TOOL (expected `national_trend`, got
   `data_quality_notes`). `compare_offices` is in the expected set; it sits in a different
   position. The real misses are `source_links` (absent) and the trend arguments. See Q7.

**Reply accuracy check** (against the payloads)

- All figures in both tables match the payloads: national 57.7% (`national_trend` FY2026
  0.5769), each office rate after rounding (Charlottesville 0.4265 gives 42.7%), decision
  counts, judge counts, and 144 offices.
- Gap of about 43 points (76.9 − 33.9). Colorado Springs about 24 below national (57.7 − 33.9 =
  23.8). Both correct.
- Region 02 has three top-ten offices (Queens, San Juan, Long Island) and none at the bottom.
  Correct. Region 03 has three of the ten lowest (Charlottesville, Harrisburg, Richmond), all in
  VA or PA. Correct. Region 04 has three high (Mobile, Charlotte, Montgomery) and one low (Atlanta
  North). Correct. Region 06 has Oklahoma City high and Little Rock low. Correct.
- **Overclaim:** "Low-allowance offices are mostly in the Midwest and Plains." Only four of the
  ten fit (Springfield MO, Topeka, Orland Park, NHC St. Louis). The other six are Colorado
  Springs (Mountain), Charlottesville, Harrisburg, Richmond (Mid-Atlantic), Atlanta North
  (Southeast), and Little Rock (South). The payload does not support "mostly". This is a model
  error, not a server error.
- **Unsourced labels:** the region names (New York and Puerto Rico, Mid-Atlantic, Southeast)
  come from outside knowledge. They are fair labels, but the tool does not return them.
- **Not delivered:** a regional trend over time. The reply is a cross-section. Its offer to
  compare FY2025 is the right next step, but it does not show a trend.
- The "provisional" caveat for FY2026 and the "no case-mix adjustment" caveat are correct.

**Verdict on the reply:** mostly correct, with one unsupported generalisation and no trend over
time. It is a better answer to the prompt as written than the expected set allows.

**Iteration #2 (F4):** not traced in this paste. The case table shows 3 calls. The token count
is derived from the averages (44.9k across two iterations, 56.9k in #1), so about 33k. Capture
its transcript before deciding whether it is the same failure. See Q6.

### 6.2 Fix plan

**Status (18 Nov 2026).** S1 and S2 are applied in `tools/national_trend.py`. E1–E4 are MCPJam
case edits. This repo has no copy of the MCPJam suite (`eval/` is the deterministic gold set,
a different suite), so those edits have to be made in the case editor. The exact text is below.

**E1. Split the case in two.** The prompt has two readings, and one case cannot require both.
- **Case A, "Rank offices by allowance rate, with regions"** (keep this prompt). Expected:
  `compare_offices(sort_by=allowance_rate)`. Response contains `allowance`. Response contains
  `ssa.gov` (replaces the `source_links` call; see E2).
- **Case B, "Regional trend over years"** (new prompt, for example "How has the allowance rate
  changed by region over the last decade?"). Expected: `national_trend(group_by=region)`. Match
  the tool and `group_by` only, without year arguments. Response contains `region`.

**E2. Remove the `source_links` expectation.** Replace it with a Response contains `ssa.gov`
check. The snapshot already carries the URL, and the server description says so.

**E3. Fill the Expected outcome field.** Draft rubric:

> Pass if the reply:
> 1. Names the highest and lowest allowance-rate hearing offices, with their rates, from a ranking tool result.
> 2. Gives each listed office's region as the data shows it.
> 3. Does not describe a regional trend over time unless it shows a multi-year series.
> 4. Gives an SSA source: an ssa.gov link, or the dataset name and as-of date.
> 5. States that rates are raw published counts, not adjusted for case mix.
> 6. Does not call any office a best or worst performer.
>
> Minor rounding, or a region label not in the data, does not fail the case.

Item 3 is the one that would have caught F3. The reply offered a cross-section and did not
claim a trend, so it passes item 3. Item 2 and item 1 pass too.

**E4. Keep the blocking response check.** "Response contains allowance" can stay blocking.

**E5. Read the Tool Calls diff with care.** It is positional (Q7). Do not treat its
WRONG TOOL labels as the verdict. Use the Selection and Tool call stages instead.

**Server changes**

**S1. Applied.** `from_fiscal_year` and `to_fiscal_year` on `ssa_alj_national_trend` no longer
say "omit to use the latest snapshot". They say omit for every year on record, and that passing
only the latest year returns one point. The shared `FiscalYear` type is unchanged, so snapshot
tools keep the old wording. Covered by
`tests/test_mcp_protocol.py::test_national_trend_year_fields_are_series_bounds`.

**S2. Applied** in the same docstring: a regional trend over time is `group_by='region'` with
both years omitted; a one-year high/low office list is `ssa_alj_compare_offices`. Re-run
"Analyze disposition trends across multiple fiscal years" (currently 2/2) after deploy, because
this is a description change on a tool that case uses.

**Do not change:**
- `source_links`. It works as designed. The `snapshot.sources` path is the reason the model
  skipped the call, and that is correct.
- `compare_offices`. It passes its own case and the call was right.
- `data_quality_notes` (B4 in §4 still applies).

**What a server change will not fix:** the "Midwest and Plains" overclaim. That is a model
error. The rubric (item 3 and item 2) is the check for it, not a tool description.

---

## 7. Wording drift to fix in the server (logged earlier, still open)

These strings disagree with the server's own instructions and with `data_quality_notes`.

| Location | Current text | Aligned text |
|---|---|---|
| `src/ssa_alj_mcp/resources/about.py` line 30 | "Rates reflect case mix and are not a measure of judge quality or correctness." | "Rates are not adjusted for case mix, and they are not a measure of judge quality or correctness." |
| `src/ssa_alj_mcp/prompts/analysis.py` line 16 (`compare_office_outcomes`) | "…and state that rates reflect case mix." | "…and state that rates are not adjusted for case mix and are not a performance rating." |
| `about.py` tool list | 13 tools; omits `business_queries` and `source_links` | List all 15 |

Keep `app.py`'s line "Allowance rates are not case-mix adjusted and are not performance
ratings." It is the correct one.

---

## 8. Open questions

| # | Question | How to answer |
|---|---|---|
| Q1 | The trace lists more tool rows than the Tool Calls tab (F1: 11 vs 9; F2: repeated rows vs 8). | Answered for F2. The message export and the Tool Calls tab each list 8 calls, once. The waterfall repeats rows with the same durations (29ms, 34ms, 119ms, 420ms, 421ms). Those repeats are a display duplicate. F1 is the same pattern until a raw trace says otherwise. |
| Q2 | Does MCPJam support an allowed-tools list, a regex assertion, or a digits-plus-percent check? | Check the assertion types in the case editor. Fall back to rubric-only if not. |
| Q3 | Iteration #2 numbers (§5). | Answered. 8 calls, 113,552 tokens, prompt latency 23.3s. See §5. |
| Q4 | Iteration dates on the run page. Are they all 18 Nov? | Answered for the F3 run: both iterations show 18/11/2026 10:51:07 on the case page. |
| Q5 | The Response stage says the reply showed the source as "[url]". The exported final message has the full URL. | Answered from the server. JSON tool results include the full `html` and `xml` strings (`services` put them on `snapshot.sources`). `formatting.py` does not rewrite links to `[url]`. The F3 reply was `response_format=json` and the exported assistant text has the full URL. `[url]` is MCPJam's display of that message, not a string the server returned. A "response contains `ssa.gov`" check should still see the URL. Confirm on the next run; if it fails while the chat shows the URL, the scorer is reading the redacted view. |
| Q6 | F4 (iteration #2) trace. Is it the same failure as F3? | Still open. The case table shows 3 calls and the averages imply about 33k tokens. There is no transcript, Tool Calls tab, or reply for iteration #2 in the materials so far. It cannot be classified, and no extra server change should be made for it, until that export is pasted. |
| Q7 | Does MCPJam compare tool calls by position or as a set? | Answered from the F3 Tool Calls tab. Expected slot 1 (`source_links`) was paired with actual call 1 (`compare_offices`) and labelled WRONG TOOL, even though `compare_offices` is in the expected set. Slot 3 (`national_trend` with `group_by=region`) was paired with actual call 3 (`data_quality_notes`). That is index pairing. There is no comparison setting in this repo. When editing the case, order the expected tools in the order a sensible session calls them (`compare_offices`, then `national_trend`), and treat WRONG TOOL on a tool that is in the expected set as a position mismatch. |

### 7.1 What was applied (18 Nov 2026)

- **B1** `services/discovery.py`: `business_queries` in custom mode now returns `scope_note`.
  It is set when the query has forecast wording (predict, forecast, projection, next year or
  fiscal, future, will, going to) or best or top performer wording. It is `null` for factual
  queries. The recipes are still returned, so the model keeps a grounded plan.
- **B2** `app.py`: instructions now include "Do not forecast future rates or name a judge as a
  best performer; the data has no forecasting model and published counts are not a performance
  rating."
- **Tests:** `tests/test_discovery.py` adds a flag test (forecast plus ranking query) and a
  clear-query test (`scope_note is None`). Lint passes. Full suite: 53 passed.
- **Not yet verified in MCPJam.** F1 and F2 both ran on the deployed `4.2.1` server, which
  does not return `scope_note`. Re-run the refusal case after the A edits and after B1–B2
  are deployed, then record the new run here.

---

## 9. How a case is scored (what we learned about MCPJam)

- **Assertions run in order and stop at the first failure.** Later checks show "assert failed
  (step 1)" and are never evaluated. In F1, `case-mix` and `No tool errors` never ran, so we
  cannot say they failed.
- **Strict vs non-strict.** A non-blocking failure is recorded but does not by itself fail the
  iteration. Blocking "no tool errors" does.
- **Expected outcome is an LLM judge.** An empty field means the judge has nothing to grade
  against, so it reports "no rubric" and advisory confidence. Always fill it in.
- **"Fail this case when a tool call returns an error"** was on for the refusal case.
- **Selection stage** compares the actual tool calls with the expected set. A "no tools"
  expectation fails on any call, even a harmless read.
- **Tool Calls diff is positional.** A call in the expected set can still show WRONG TOOL if it
  sits in a different position (F3). Use the Selection and Tool call stages as the verdict.
- **The Response stage can misquote the reply.** F3's scorecard says the source was shown as
  "[url]". The exported message has the full URL. Check the raw input before trusting a Response
  verdict on links (Q5).

---

## 10. Passing cases: do not disturb

Recorded as a regression list. Prompts are not copied here.

- **Business-queries catalog** passes. An empty query returns the 10 recipes. The custom match
  on the refusal prompt returned recipes, which shows the tool ran. It did not stop the model
  from forecasting anyway.
- **Compare office allowance rates and rank by results** passes. `compare_offices` is fine for
  a ranking question.
- **Multi-year disposition trends** passes. `national_trend` with `group_by="national"` is
  selected for a plain trend question.
- **Judge profile** and **search, then profile, then verify sources** pass. The changes most
  likely to break these are a blanket "call no tools on judge questions" rule and edits to
  `get_judge_profile`'s description.

---

## 11. Log

| Date | Note |
|---|---|
| 18 Nov 2026 | MCPJam Run #1 (claude-haiku-5.5), 10/14 iterations passed. |
| 18 Nov 2026 | This file opened from the run screenshot, the refusal case page, and one full transcript of the refusal prompt. No code changes. |
| 18 Nov 2026 | F1 traced to run `mh7b6pbj` (9 calls, 122,975 tokens). Earlier model name, date, and F2 numbers corrected. Fix plan A and B drafted. No code changes yet. |
| 18 Nov 2026 | Decision: eval fixes A plus server guardrails B1 and B2. Applied B1 and B2 with two tests (53 passed, ruff clean). A1 to A6 are to be made in the MCPJam UI. B3 and B4 not applied. |
| 18 Nov 2026 | F2 traced (same run `mh7b6pbj`): 8 calls, 113,552 tokens, 23.3s. Same two scored failures as F1 (zero-tool rule, exact phrase). Reply still gives hedged next-year ranges (Walker 80–93%, Kadlec 10–20%). No new server change. A6 must fail a range even when the reply says "not a forecast". `business_queries` payload has no `scope_note`, so B1 was not on this server. |
| 18 Nov 2026 | F3 traced (run `mh7b6pbj`, iteration #1; prompt and expected set now recorded): 4 calls, 56,852 tokens, 16.4s. Missing `source_links` (server already returns snapshot sources, so the expectation conflicts with the design). Trend call was `national_trend` FY2026 only with no `group_by`. Likely cause: `from_fiscal_year` schema text says "omit to use latest", which is wrong for this tool. Reply figures all match payloads; one overclaim ("mostly Midwest and Plains", 4 of 10). Advisory judge passed it despite its own listed misses. |
| 18 Nov 2026 | Applied S1 and S2 on `ssa_alj_national_trend`: year fields describe a series (omit = every year on record), and the description points regional-over-time questions at `group_by=region` and one-year office rankings at `compare_offices`. Schema test added. 54 passed, ruff clean. E1–E4 remain MCPJam UI edits (text in §6.2). Q5: `[url]` is not produced by the server. Q7: Tool Calls diff is index pairing. Q6 (F4 transcript) still needs a paste. |
