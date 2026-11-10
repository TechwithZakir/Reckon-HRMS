"""Per-person pay amounts for the Run salary list: each component, additions, deductions and gross.

Each component starts from the person's salary structure (same formula engine as the payslip preview).
The run's Additional Salary then changes it, as HRMS does on the slip:
- an approved change with "overwrite salary structure amount" replaces the component's amount;
- any other approved Additional Salary (festival bonus, late and early deduction) is added to it.
Drafts are pending approval and do not count. Income tax is worked out on the slip, so it is not here.
"""

from __future__ import annotations

import frappe
from frappe.utils import flt


def person_amounts(doc, employees: list[str]) -> dict[str, dict]:
    from reckon_hrms.api.salary import structure_amounts

    if not employees:
        return {}
    assignments: dict[str, object] = {}
    for row in frappe.get_all("Salary Structure Assignment", filters={
            "employee": ["in", employees], "docstatus": 1, "from_date": ["<=", doc.end_date]},
            fields=["employee", "salary_structure", "base"], order_by="from_date desc", limit_page_length=0):
        assignments.setdefault(row.employee, row)

    rows = frappe.get_all("Additional Salary", filters={
        "employee": ["in", employees], "payroll_date": ["between", [doc.start_date, doc.end_date]],
        "docstatus": ["!=", 2]},
        fields=["employee", "salary_component", "amount", "docstatus", "overwrite_salary_structure_amount"],
        limit_page_length=0)
    kinds: dict[str, str] = dict(frappe.get_all("Salary Component", filters={
        "name": ["in", list({r.salary_component for r in rows}) or [""]]},
        fields=["name", "type"], as_list=True, limit_page_length=0))

    pending: dict[str, int] = {emp: 0 for emp in employees}
    overwrites: dict[str, dict[str, float]] = {}
    adds: dict[str, dict[str, float]] = {}
    for row in rows:
        if row.docstatus == 0:
            pending[row.employee] = pending.get(row.employee, 0) + 1
            continue
        target = overwrites if row.overwrite_salary_structure_amount else adds
        bucket = target.setdefault(row.employee, {})
        bucket[row.salary_component] = bucket.get(row.salary_component, 0.0) + flt(row.amount)

    overtime: dict[str, float] = {emp: 0.0 for emp in employees}
    for row in frappe.get_all("Overtime Slip", filters={
            "employee": ["in", employees], "docstatus": ["!=", 2],
            "start_date": [">=", doc.start_date], "end_date": ["<=", doc.end_date]},
            fields=["employee", "total_overtime_duration"], limit_page_length=0):
        overtime[row.employee] = overtime.get(row.employee, 0.0) + flt(row.total_overtime_duration)

    cache: dict[tuple, dict] = {}
    out = {}
    for emp in employees:
        assignment = assignments.get(emp)
        lines: list[tuple[str, str, float]] = []
        if assignment:
            key = (assignment.salary_structure, flt(assignment.base))
            if key not in cache:
                cache[key] = structure_amounts(assignment.salary_structure, assignment.base)
            lines = cache[key]["lines"]

        person: dict[str, float] = {}
        for component, kind, amount in lines:
            kinds.setdefault(component, kind)
            person[component] = flt(amount)
        for component, amount in overwrites.get(emp, {}).items():
            person[component] = amount
        for component, amount in adds.get(emp, {}).items():
            person[component] = round(person.get(component, 0.0) + amount, 2)
        person = {c: round(v, 2) for c, v in person.items()}

        basic = round(person.get("Basic Salary", 0.0), 2)
        additions = round(sum(v for c, v in person.items()
                              if c != "Basic Salary" and kinds.get(c, "Earning") == "Earning"), 2)
        deductions = round(sum(v for c, v in person.items() if kinds.get(c) == "Deduction"), 2)
        out[emp] = {
            "basic": basic, "additions": additions, "deductions": deductions,
            "gross": round(basic + additions, 2), "components": person,
            "overtime_hours": round(overtime.get(emp, 0.0), 2), "pending_requests": pending.get(emp, 0),
            "structure": assignment.salary_structure if assignment else None,
            "base": flt(assignment.base) if assignment else 0.0,
        }
    return out


def component_kinds(names: list[str]) -> dict[str, str]:
    """Earning or Deduction for each component name, for the table's column order."""
    if not names:
        return {}
    return dict(frappe.get_all("Salary Component", filters={"name": ["in", names]},
                               fields=["name", "type"], as_list=True, limit_page_length=0))
