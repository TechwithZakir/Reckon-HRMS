"""Per-person pay amounts for the Run salary list: basic, additions, deductions and gross.

Built from the person's current salary structure (same formula engine as the payslip preview), plus
the run's Additional Salary: submitted ones count, draft ones are pending approval and do not.
Income tax is worked out on the slip, so it is not here.
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

    extra = {emp: {"additions": 0.0, "deductions": 0.0, "pending": 0} for emp in employees}
    rows = frappe.get_all("Additional Salary", filters={
        "employee": ["in", employees], "payroll_date": ["between", [doc.start_date, doc.end_date]],
        "docstatus": ["!=", 2]}, fields=["employee", "salary_component", "amount", "docstatus"],
        limit_page_length=0)
    component_types = dict(frappe.get_all("Salary Component", filters={
        "name": ["in", list({r.salary_component for r in rows}) or [""]]},
        fields=["name", "type"], as_list=True, limit_page_length=0))
    for row in rows:
        bucket = extra.setdefault(row.employee, {"additions": 0.0, "deductions": 0.0, "pending": 0})
        if row.docstatus == 0:
            bucket["pending"] += 1
        elif component_types.get(row.salary_component) == "Deduction":
            bucket["deductions"] += flt(row.amount)
        else:
            bucket["additions"] += flt(row.amount)

    # One line per component for each person: structure pay items, plus the run's Additional Salary
    # (festival bonus, late and early deduction, approved changes) under their own component.
    components: dict[str, dict[str, float]] = {emp: {} for emp in employees}
    for row in rows:
        if row.docstatus == 0:
            continue
        bucket = components.setdefault(row.employee, {})
        bucket[row.salary_component] = bucket.get(row.salary_component, 0.0) + flt(row.amount)
    kinds: dict[str, str] = dict(component_types)

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
        amounts = {"basic": 0.0, "additions": 0.0, "gross": 0.0, "deductions": 0.0, "lines": []}
        if assignment:
            key = (assignment.salary_structure, flt(assignment.base))
            if key not in cache:
                cache[key] = structure_amounts(assignment.salary_structure, assignment.base)
            amounts = cache[key]
        person = {}
        for component, kind, amount in amounts.get("lines", []):
            kinds.setdefault(component, kind)
            person[component] = round(person.get(component, 0.0) + flt(amount), 2)
        for component, amount in components.get(emp, {}).items():
            person[component] = round(person.get(component, 0.0) + amount, 2)
        adj = extra.get(emp, {"additions": 0.0, "deductions": 0.0, "pending": 0})
        additions = round(flt(amounts["additions"]) + adj["additions"], 2)
        deductions = round(flt(amounts["deductions"]) + adj["deductions"], 2)
        basic = round(flt(amounts["basic"]), 2)
        out[emp] = {
            "basic": basic, "additions": additions, "deductions": deductions,
            "components": person, "overtime_hours": round(overtime.get(emp, 0.0), 2),
            "gross": round(basic + additions, 2), "pending_requests": adj["pending"],
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
