"""Two-character codes for salary components, used as short column headings on slip tables and the PDF.

Pure rules, no Frappe import. The first letters of the first two meaningful words are used
("Basic Salary" -> BS). Where two components give the same code, the second gets a digit
("BS", "B2"), so every component keeps its own column.
"""

from __future__ import annotations

import re

STOP_WORDS = {"and", "of", "the", "for", "to", "on"}


def short_code(name: str) -> str:
    words = [w for w in re.findall(r"[A-Za-z]+", name) if w.lower() not in STOP_WORDS]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    if words:
        return (words[0][:2] + "X")[:2].upper()
    return "XX"


def short_codes(names: list[str]) -> dict[str, str]:
    """A code for each name, in the order given, unique within the list."""
    codes: dict[str, str] = {}
    used: set[str] = set()
    for name in names:
        base = short_code(name)
        code = base
        digit = 2
        while code in used:
            code = base[0] + str(digit)
            digit += 1
        used.add(code)
        codes[name] = code
    return codes
