"""The setup review: after setup, each step with what it holds and a link to review or edit it (pure: no Frappe).

``rows(facts, studio)`` turns counts the site gathered into the lines the Guided setup tab shows. A step with nothing yet
offers "Set up now", which starts that step of the setup chat; a finished step offers a link to its own list or record.
"""

from __future__ import annotations

import re


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def rows(facts: dict, studio: str = "hr") -> list[dict]:
    """``facts``: company, country, language, industry_label, branches, departments, designations, holiday_list (name or ""),
    named_holidays, weekly_off (list), shifts, leave_policies, structures, assignments, components."""
    company = facts["company"]
    holiday_list = facts.get("holiday_list") or ""
    weekly = ", ".join(facts.get("weekly_off") or [])
    hr = [
        {"key": "country", "label": "Country", "done": bool(facts.get("country")), "detail": facts.get("country") or "Not set",
         "doctype": "Company", "name": company, "chat": "country"},
        {"key": "language", "label": "Language", "done": bool(facts.get("language")), "detail": facts.get("language") or "Not set",
         "doctype": "User", "name": facts.get("user"), "chat": "language"},
        {"key": "industry", "label": "Industry", "done": bool(facts.get("industry_label")), "detail": facts.get("industry_label") or "Not chosen",
         "doctype": "Company", "name": company, "chat": "industry"},
        {"key": "locations", "label": "Locations", "done": facts.get("branches", 0) > 0, "detail": _count(facts.get("branches", 0), "branch", "branches"),
         "doctype": "Branch", "name": None, "chat": "locations"},
        {"key": "departments", "label": "Departments", "done": facts.get("departments", 0) > 0,
         "detail": _count(facts.get("departments", 0), "department", "departments"), "doctype": "Department", "name": None, "chat": "extra_departments"},
        {"key": "titles", "label": "Job titles", "done": facts.get("designations", 0) > 0,
         "detail": _count(facts.get("designations", 0), "job title", "job titles"), "doctype": "Designation", "name": None, "chat": "extra_titles"},
        {"key": "holidays", "label": "Weekly off and holidays", "done": bool(holiday_list) and (bool(weekly) or facts.get("named_holidays", 0) > 0),
         "detail": (f"Weekly off: {weekly or 'none'}; " + _count(facts.get("named_holidays", 0), "public holiday", "public holidays")) if holiday_list else "No holiday list yet",
         "doctype": "Holiday List", "name": holiday_list or None, "chat": "weekly_off"},
        {"key": "shift", "label": "Working hours", "done": facts.get("shifts", 0) > 0, "detail": _count(facts.get("shifts", 0), "shift", "shifts"),
         "doctype": "Shift Type", "name": None, "chat": "shift"},
        {"key": "leave", "label": "Leave policy", "done": facts.get("leave_policies", 0) > 0,
         "detail": _count(facts.get("leave_policies", 0), "leave policy", "leave policies"), "doctype": "Leave Policy", "name": None, "chat": "leave"},
    ]
    payroll = [
        {"key": "industry", "label": "Industry", "done": bool(facts.get("industry_label")), "detail": facts.get("industry_label") or "Not chosen",
         "doctype": "Company", "name": company, "chat": "industry"},
        {"key": "components", "label": "Pay items", "done": facts.get("components", 0) > 0, "detail": _count(facts.get("components", 0), "pay item", "pay items"),
         "doctype": "Salary Component", "name": None, "chat": "structure"},
        {"key": "structure", "label": "Salary structure", "done": facts.get("structures", 0) > 0,
         "detail": _count(facts.get("structures", 0), "salary structure", "salary structures"), "doctype": "Salary Structure", "name": None, "chat": "structure"},
        {"key": "assignments", "label": "Structures given to people", "done": facts.get("assignments", 0) > 0,
         "detail": _count(facts.get("assignments", 0), "assignment", "assignments"), "doctype": "Salary Structure Assignment", "name": None, "chat": None},
    ]
    return payroll if studio == "payroll" else hr


LEAVE_FIELDS = {"Casual Leave": "leave_casual", "Sick Leave": "leave_sick", "Earned Leave": "leave_earned", "Maternity Leave": "leave_maternity"}
_FORMULA = re.compile(r"^\s*base\s*\*\s*([0-9]+(?:\.[0-9]+)?)\s*$")


def _g(value) -> str:
    return f"{float(value):g}"


def strip_suffix(name: str, suffix: str) -> str:
    """"Standard Structure - Acme Ltd." with suffix "Acme Ltd." -> "Standard Structure"."""
    tail = f" - {suffix}"
    return name[: -len(tail)] if suffix and name.endswith(tail) else name


def shift_answers(name: str, start, end, grace, abbr: str = "") -> dict:
    """The company's shift as interview answers (times as HH:MM)."""
    out = {"shift_name": strip_suffix(name, abbr), "shift_start": str(start)[:5].rjust(5, "0"), "shift_end": str(end)[:5].rjust(5, "0")}
    if grace:
        out["late_grace"] = str(int(grace))
    return out


def leave_answers(details: list[dict]) -> dict:
    """A Leave Policy's rows as interview answers: ``[{"leave_type": ..., "annual_allocation": ...}]``."""
    return {LEAVE_FIELDS[d["leave_type"]]: _g(d["annual_allocation"]) for d in details if d.get("leave_type") in LEAVE_FIELDS and d.get("annual_allocation")}


def structure_answers(name: str, company: str, earnings: list[dict]) -> dict:
    """A Salary Structure as interview answers. A percent is only read back when the formula is a plain percent of the gross."""
    out = {"structure_name": strip_suffix(name, company)}
    for row in earnings:
        component, formula = row.get("salary_component"), row.get("formula") or ""
        match = _FORMULA.match(formula) if row.get("amount_based_on_formula") else None
        if component == "Basic Salary" and match:
            out["basic_pct"] = _g(float(match.group(1)) * 100)
        elif component == "House Rent Allowance" and match:
            out["hra_pct"] = _g(float(match.group(1)) * 100)
        elif component == "Medical Allowance" and not formula and row.get("amount"):
            out["medical_amount"] = _g(row["amount"])
        elif component == "Conveyance Allowance" and not formula and row.get("amount"):
            out["conveyance_amount"] = _g(row["amount"])
    return out


def holiday_answers(country_set: bool, weekly: list[str], named: list[dict]) -> dict:
    """The holiday list as interview answers: the weekly off days, and either "from the calendar" or the named holidays."""
    out = {"weekly_off": list(weekly)}
    if country_set:
        out["holidays_country"] = "1"
    elif named:
        out["holidays"] = "\n".join(f"{h['date']} {h['name']}" for h in named)
    return out


def finished(rows_: list[dict]) -> bool:
    """Setup counts as done when the industry is chosen and most steps hold something."""
    industry = next((r for r in rows_ if r["key"] == "industry"), None)
    return bool(industry and industry["done"] and sum(r["done"] for r in rows_) >= max(3, len(rows_) - 3))
