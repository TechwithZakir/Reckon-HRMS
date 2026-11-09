"""Plain-language description of a salary component's calculation, for the payslip preview.

Pure data, no Frappe import, so it can be unit-tested. The preview shows how each line was worked
out next to its amount, so an HR user can see the percentage and the source without reading formulas.
"""

from __future__ import annotations

import re

_PERCENT_OF = re.compile(r"\s*(\w+)\s*\*\s*([0-9]+(?:\.[0-9]+)?)\s*")


def describe(formula: str | None, amount_based_on_formula: bool, labels: dict[str, str],
             condition: str | None = None) -> str:
    """Return text such as "60% of base salary", "50% of Basic Salary", "Fixed amount" or the formula.

    ``labels`` maps a component abbreviation to its name. ``base`` is the structure's base salary.
    """
    if not (amount_based_on_formula and formula):
        text = "Fixed amount"
    else:
        match = _PERCENT_OF.fullmatch(formula)
        if match:
            source, factor = match.group(1), float(match.group(2))
            name = "base salary" if source == "base" else labels.get(source, source)
            text = f"{factor * 100:g}% of {name}"
        else:
            text = f"Formula: {formula.strip()}"
    if condition:
        text += f" (only when {condition.strip()})"
    return text
