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
        # The industry is a starter template chosen once, not a record: there is no page to open, only the picker.
        {"key": "industry", "label": "Industry template", "done": bool(facts.get("industry_label")), "detail": facts.get("industry_label") or "Not chosen",
         "doctype": None, "name": None, "chat": "industry"},
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


def payroll_groups(f: dict) -> list[dict]:
    """The salary process in the order Frappe HRMS needs it. What belongs to HR Studio is shown as a status with a link, never asked again.

    ``f``: employees, holiday_list, shifts, leave_policies, payable_account, components, structures, active, assigned,
    rules (marks_per_day, divisor, cap), last_run (name, status) or None.
    """
    def row(key, label, done, detail, actions):
        return {"key": key, "label": label, "done": bool(done), "detail": detail, "actions": actions}

    hr = [
        row("employees", "Employees", f["employees"] > 0, _count(f["employees"], "employee", "employees"),
            [{"kind": "hr", "stage": "company", "label": "Add in HR Studio"}] if f["employees"] == 0 else [{"kind": "open", "doctype": "Employee", "label": "Review / edit"}]),
        row("holidays", "Holiday calendar", bool(f.get("holiday_list")), "Set" if f.get("holiday_list") else "Not set",
            [{"kind": "hr", "stage": "guided", "label": "Set up in HR Studio"}] if not f.get("holiday_list") else [{"kind": "open", "doctype": "Holiday List", "name": f["holiday_list"], "label": "Review / edit"}]),
        row("attendance", "Attendance and working hours", f["shifts"] > 0, _count(f["shifts"], "shift", "shifts"),
            [{"kind": "hr", "stage": "attendance", "label": "Set up in HR Studio"}] if f["shifts"] == 0 else [{"kind": "open", "doctype": "Shift Type", "label": "Review / edit"}]),
        row("leave", "Leave policy", f["leave_policies"] > 0, _count(f["leave_policies"], "leave policy", "leave policies"),
            [{"kind": "hr", "stage": "guided", "label": "Set up in HR Studio"}] if f["leave_policies"] == 0 else [{"kind": "open", "doctype": "Leave Policy", "label": "Review / edit"}]),
    ]
    rules = f.get("rules") or {}
    rule_text = (f"Every {rules['marks_per_day']} late or early marks = 1 day, pay / {rules['divisor']}, " + (f"cap {rules['cap']:g}" if rules.get("cap") else "no cap")) if rules.get("marks_per_day") else "Standard: every 3 marks = 1 day, pay / 30, no cap"
    last = f.get("last_run")
    pay = [
        row("payable", "Payroll payable account", bool(f.get("payable_account")), f["payable_account"] if f.get("payable_account") else "Not set: a salary run cannot be created without it",
            [{"kind": "fix", "label": "Set it up"}] if not f.get("payable_account") else [{"kind": "open", "doctype": "Company", "name": f.get("company"), "label": "Review / edit"}]),
        row("components", "Pay items", f["components"] > 0, _count(f["components"], "pay item", "pay items"),
            [{"kind": "hr", "stage": "guided", "label": "Load from your industry"}] if f["components"] == 0 else [{"kind": "open", "doctype": "Salary Component", "label": "Review / edit"}]),
        row("structure", "Salary structure", f["structures"] > 0, _count(f["structures"], "salary structure", "salary structures"),
            [{"kind": "agent", "label": "✦ Set up with Ask AI"}] if f["structures"] == 0 else [{"kind": "open", "doctype": "Salary Structure", "label": "Review / edit"}]),
        row("rules", "Late and early deduction rule", True, rule_text, [{"kind": "rules", "label": "Edit"}]),
        row("assignments", "Structure given to people", f["active"] > 0 and f["assigned"] >= f["active"],
            f"{f['assigned']} of {f['active']} active people have a structure",
            ([{"kind": "stage", "stage": "salary", "label": "Give structure to people"}] if f["active"] and f["assigned"] < f["active"] else [{"kind": "open", "doctype": "Salary Structure Assignment", "label": "Review / edit"}])
            + ([{"kind": "stage", "stage": "salary", "label": "Paid different amounts? Set each person's gross"}] if f["active"] else [])),
        row("run", "Run salary", bool(last and last.get("status") == "Paid"), (f"Latest run {last['name']}: {last['status']}" if last else "No run yet"),
            [{"kind": "stage", "stage": "run", "label": "Open Run salary"}]),
    ]
    return [{"title": "Already handled in HR Studio", "rows": hr}, {"title": "Payroll, in the order HRMS needs it", "rows": pay}]


def hr_pending(groups: list[dict]) -> list[dict]:
    """The HR Studio steps that are not done yet. Payroll comes after them: people, holidays, hours and leave feed every salary slip."""
    return [{"key": r["key"], "label": r["label"], "detail": r["detail"], "actions": r["actions"]}
            for g in groups[:1] for r in g["rows"] if not r["done"]]


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
