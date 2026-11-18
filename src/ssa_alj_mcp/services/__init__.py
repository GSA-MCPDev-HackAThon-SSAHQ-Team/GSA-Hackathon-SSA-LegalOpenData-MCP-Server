"""Query services used by the MCP tools (sync functions, JSON-serialisable dicts)."""

from . import analysis, discovery, judges, offices, quality, reports, trends, workforce
from .analysis import outlier_report, within_office_variation
from .discovery import business_queries, source_links
from .judges import get_judge_profile, search_judges
from .offices import compare_offices, get_office_profile, office_processing_ranking
from .quality import data_quality_notes
from .reports import list_reports
from .trends import compare_periods, monthly_pace, national_trend
from .workforce import judge_movements

__all__ = [
    "analysis",
    "business_queries",
    "compare_offices",
    "compare_periods",
    "data_quality_notes",
    "discovery",
    "get_judge_profile",
    "get_office_profile",
    "judge_movements",
    "judges",
    "list_reports",
    "monthly_pace",
    "national_trend",
    "office_processing_ranking",
    "offices",
    "outlier_report",
    "quality",
    "reports",
    "search_judges",
    "source_links",
    "trends",
    "within_office_variation",
    "workforce",
]
