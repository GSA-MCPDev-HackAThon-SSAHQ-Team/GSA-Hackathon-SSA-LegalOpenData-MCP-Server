# Guardrails

Rules for free-text arguments on this read-only public dataset. The code that
enforces them is `rules.py` in this folder. Tool wrappers call `refusal()`
before they query SQLite. `ssa_alj_business_queries` also calls `scope_note()`
for forecast and performance-ranking questions.

## What a rule may do

| Function | Effect |
|---|---|
| `scope_note` | The tool still returns recipes, plus a note. Used for forecasts and "best performer" wording. |
| `refusal` | The tool returns an error and does not query the database. Used for personal data and inputs that try to change the server's instructions or query the database directly. |

A refusal names the rule id in logs (`guardrail refused rule=pii.ssn`). It does not log or return the text that matched.

Published ALJ and office names are public data. Do not add a rule that refuses an ordinary name.

## Add a rule

1. Append a `_rule(...)` in `_REFUSALS` in `rules.py`, or extend the forecast / ranking expressions if the case is advisory.
2. Pick an id: `pii.<thing>` or `security.<thing>`.
3. Add a test in `tests/test_guardrails.py` that the reply does not contain the sample input.
4. Run `uv run pytest tests/test_guardrails.py tests/test_discovery.py -q`.

Deploy is the normal Render deploy of `main`. There is no separate guardrail service.
