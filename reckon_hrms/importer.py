"""People import rules (Page 1). Pure Python: parsing, checking and suggesting fixes.

Each row is checked against the company's offices, departments, job titles, levels and types of employee.
Errors are returned as data (row number, name, plain message, suggestion), never raised.
"""

from __future__ import annotations

import csv
import difflib
import io
import re
from datetime import date, datetime

TEMPLATE_COLUMNS = [
    "first_name", "last_name", "gender", "date_of_birth", "date_of_joining", "cell_number",
    "department", "designation", "branch", "grade", "employment_type", "company",
]
REQUIRED = ["first_name", "gender", "date_of_birth", "date_of_joining", "department", "designation"]
GENDERS = {"male", "female", "other"}
DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d %B %Y")
PHONE_RE = re.compile(r"^01[3-9]\d{8}$")  # Bangladesh mobile numbers: 11 digits starting 013-019


def template_csv() -> str:
    buf = io.StringIO()
    csv.writer(buf).writerow(TEMPLATE_COLUMNS)
    return buf.getvalue()


def parse_date(text: str) -> date | None:
    value = (text or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def suggest(name: str, options: list[str]) -> str | None:
    """A near match from the list, for a one-click fix."""
    matches = difflib.get_close_matches(name, options, n=1, cutoff=0.75)
    return matches[0] if matches else None


def check_rows(rows: list[dict], known: dict[str, set[str]], today: date | None = None) -> dict:
    """known: {"department": {...}, "designation": {...}, "branch": {...}, "grade": {...},
    "employment_type": {...}}. Returns counts and the first errors. Row numbers start at 2 (after header)."""
    today = today or date.today()
    valid, errors = [], []
    for index, row in enumerate(rows, start=2):
        name = " ".join(filter(None, [row.get("first_name", "").strip(), row.get("last_name", "").strip()])) or "(no name)"
        problems = []

        for field in REQUIRED:
            if not (row.get(field) or "").strip():
                problems.append((field, f"{field.replace('_', ' ').capitalize()} is missing."))

        gender = (row.get("gender") or "").strip().lower()
        if gender and gender not in GENDERS:
            problems.append(("gender", "Gender must be Male, Female or Other."))

        joined = parse_date(row.get("date_of_joining", ""))
        if (row.get("date_of_joining") or "").strip() and joined is None:
            problems.append(("date_of_joining", "Joining date is not a date we understand. Use 2026-07-01 or 01-07-2026."))
        elif joined and joined > today:
            problems.append(("date_of_joining", "Joining date is in the future."))

        dob_text = (row.get("date_of_birth") or "").strip()
        if dob_text:
            dob = parse_date(dob_text)
            if dob is None:
                problems.append(("date_of_birth", "Date of birth is not a date we understand."))

        phone = re.sub(r"[\s\-]", "", row.get("cell_number") or "")
        if phone and not PHONE_RE.match(phone):
            problems.append(("cell_number", "Phone number must be 11 digits starting 013 to 019."))

        for field in ("department", "designation", "branch", "grade", "employment_type"):
            value = (row.get(field) or "").strip()
            if value and value not in known.get(field, set()):
                fix = suggest(value, sorted(known.get(field, set())))
                text = f"{field.replace('_', ' ').capitalize()} '{value}' not found."
                problems.append((field, text + (f" Did you mean '{fix}'?" if fix else " Add it in section 2 first.")))

        if problems:
            field, message = problems[0]
            errors.append({"row": index, "name": name, "field": field, "message": message,
                           "fields": [f for f, _m in problems],
                           "problems": [m for _f, m in problems],
                           "suggestion": suggest_value(problems, row, known)})
        else:
            valid.append({"row": index, "data": row})
    return {"read": len(rows), "ready": len(valid), "to_fix": len(rows) - len(valid),
            "errors": errors[:50], "valid": valid}


def suggest_value(problems, row, known) -> str | None:
    """The suggested replacement for the first master-name problem, if there is one."""
    for field, _message in problems:
        if field in known:
            value = (row.get(field) or "").strip()
            fix = suggest(value, sorted(known[field]))
            if fix:
                return fix
    return None
