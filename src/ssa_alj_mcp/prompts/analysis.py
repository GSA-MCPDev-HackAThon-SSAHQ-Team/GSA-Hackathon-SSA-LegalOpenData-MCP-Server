"""Prompt templates for common ALJ data questions."""

from __future__ import annotations

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.prompt(name="compare_office_outcomes")
    def compare_office_outcomes(fiscal_year: int = 2024, region: str = "") -> str:
        """Compare hearing offices' outcomes for a fiscal year."""
        scope = f" in region {region}" if region else ""
        return (
            f"Using the SSA ALJ tools, compare hearing offices{scope} for fiscal year {fiscal_year}. "
            "Use min_decisions to skip tiny offices, report the highest and lowest allowance rates "
            "with their decision counts and the as-of date, and state that rates reflect case mix."
        )

    @mcp.prompt(name="judge_summary")
    def judge_summary(judge_name: str) -> str:
        """Summarise one judge's published record."""
        return (
            f"Find the SSA judge '{judge_name}' with ssa_alj_search_judges, then use "
            "ssa_alj_get_judge_profile. Summarise decisions, allowance rate versus the national rate "
            "by fiscal year, and any office changes. Mention that matching is by name only."
        )
