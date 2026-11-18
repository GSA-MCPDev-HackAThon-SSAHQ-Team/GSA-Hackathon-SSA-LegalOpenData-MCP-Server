"""Known hearing-office renames / splits (best-effort).

SSA publishes office names that change over time. Movement tools treat these as the same
logical office so a rename is not reported as a mass departure.
"""

from __future__ import annotations

# Canonical key (office_base form) -> aliases that should merge into it.
# Keys and values are compared after office_base() normalisation in callers when needed;
# entries here are already upper-case city-style bases.
OFFICE_ALIASES: dict[str, str] = {
    # Historical name -> current / preferred canonical base
    "HOUSTON-BISSONNET": "HOUSTON WEST",
    "HOUSTON BISSONNET": "HOUSTON WEST",
    "PHOENIX": "PHOENIX DOWNTOWN",
    "WEST DES MOINES": "DES MOINES",
}


def canonical_office(base: str) -> str:
    """Map a city-level office base name through the alias table."""
    key = base.upper().strip()
    return OFFICE_ALIASES.get(key, key)
