"""Unit tests for the pure helpers."""

from __future__ import annotations

from ssa_alj_mcp.utils import error, normalize_key, paginate, rate


def test_normalize_key_folds_case_and_punctuation():
    assert normalize_key("Akins, George M.") == normalize_key("AKINS  George M") == "akins george m"


def test_paginate_envelope():
    page = paginate(list(range(5)), limit=2, offset=0)
    assert page["items"] == [0, 1] and page["has_more"] and page["next_offset"] == 2
    last = paginate(list(range(5)), limit=2, offset=4)
    assert last["items"] == [4] and not last["has_more"] and last["next_offset"] is None


def test_paginate_clamps_limit_and_offset():
    page = paginate(list(range(500)), limit=10_000, offset=-5)
    assert page["count"] == 100 and page["offset"] == 0


def test_rate_handles_zero_and_none():
    assert rate(1, 4) == 0.25
    assert rate(1, 0) is None and rate(None, 5) is None


def test_error_payload():
    assert error("boom", "try x", code=1) == {"error": "boom", "hint": "try x", "code": 1}
