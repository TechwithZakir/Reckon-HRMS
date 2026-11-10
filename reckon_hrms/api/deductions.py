"""Late-entry and early-exit deductions for a salary run: preview, then HR approves and they are applied.

Nothing is deducted until an HR manager applies it. Each applied deduction is an Additional Salary
for the run's month, with the marks, days and rate written in its notes.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from reckon_hrms import industry_seed
from reckon_hrms.attendance_deduction import (
    DEFAULT_CAP,
    DEFAULT_DIVISOR,
    DEFAULT_MARKS_PER_DAY,
    days_deducted,
    deduction_amount,
    marks_for_days,
)

DEDUCTION_COMPONENT = "Late and Early Deduction"
APPROVE_ROLES = ["HR Manager", "Payroll Manager", "System Manager"]


def _policy(company: str) -> tuple[int, int, float]:
    row = frappe.db.get_value("Company", company, ["reckon_marks_per_day", "reckon_deduction_divisor",
                                                   "reckon_deduction_cap"], as_dict=True) or {}

    def pick(value, default):
        return default if value is None or value == "" else value

    return (int(pick(row.get("reckon_marks_per_day"), DEFAULT_MARKS_PER_DAY)),
            int(pick(row.get("reckon_deduction_divisor"), DEFAULT_DIVISOR)),
            flt(pick(row.get("reckon_deduction_cap"), DEFAULT_CAP)))


def _rows(name: str) -> tuple[object, list[dict]]:
    doc = frappe.get_doc("Payroll Entry", name)
    people = [r.employee for r in doc.employees]
    per_day, divisor, cap = _policy(doc.company)
    attendance: dict[str, list] = {}
    if people:
        for row in frappe.get_all("Attendance", filters={
                "employee": ["in", people], "docstatus": 1,
                "attendance_date": ["between", [doc.start_date, doc.end_date]]},
                fields=["employee", "status", "late_entry", "early_exit"], limit_page_length=0):
            attendance.setdefault(row.employee, []).append(row)
    bases: dict[str, float] = {}
    if people:
        for row in frappe.get_all("Salary Structure Assignment", filters={
                "employee": ["in", people], "docstatus": 1, "from_date": ["<=", doc.end_date]},
                fields=["employee", "base"], order_by="from_date desc", limit_page_length=0):
            bases.setdefault(row.employee, flt(row.base))
    applied = set(frappe.get_all("Additional Salary", filters={
        "salary_component": DEDUCTION_COMPONENT, "employee": ["in", people or [""]],
        "payroll_date": ["between", [doc.start_date, doc.end_date]], "docstatus": ["!=", 2]},
        pluck="employee")) if people else set()

    names = {r.employee: r.employee_name for r in doc.employees}
    out = []
    for emp in people:
        marks = marks_for_days(attendance.get(emp, []))
        if not marks:
            continue
        days = days_deducted(marks, per_day)
        out.append({
            "employee": emp, "employee_name": names.get(emp), "marks": marks, "days": days,
            "base": bases.get(emp, 0.0),
            "amount": deduction_amount(bases.get(emp, 0.0), days, divisor, cap),
            "already_applied": emp in applied,
        })
    policy = {"marks_per_day": per_day, "divisor": divisor, "cap": cap}
    return doc, out, policy


@frappe.whitelist(methods=["GET"])
def attendance_deductions(name: str) -> dict:
    """Who has late or early marks this run, what that deducts, and whether it is already applied."""
    frappe.only_for(APPROVE_ROLES)
    _doc, rows, policy = _rows(name)
    return {"rows": rows, "policy": policy, "total": round(sum(r["amount"] for r in rows if not r["already_applied"]), 2)}


@frappe.whitelist(methods=["POST"])
def apply_attendance_deductions(name: str, employees: list | str) -> dict:
    """HR approves: one Additional Salary deduction per chosen person. Only before salary slips exist."""
    frappe.only_for(APPROVE_ROLES)
    if isinstance(employees, str):
        employees = frappe.parse_json(employees)
    doc, rows, policy = _rows(name)
    if doc.docstatus != 0:
        frappe.throw(_("This run is no longer a draft."))
    if frappe.db.exists("Salary Slip", {"payroll_entry": name, "docstatus": ["!=", 2]}):
        frappe.throw(_("Apply attendance deductions before creating salary slips."))

    industry_seed._component(DEDUCTION_COMPONENT)
    industry_seed._ensure_component_account(doc.company, DEDUCTION_COMPONENT)

    chosen = set(employees or [])
    month = str(doc.start_date)[:7]
    created = []
    for row in rows:
        if row["employee"] not in chosen or row["already_applied"] or row["days"] <= 0 or row["amount"] <= 0:
            continue
        note = (f"{row['marks']} late or early mark(s) in {month}: {row['days']} day(s) at "
                f"base / {policy['divisor']}. Approved by {frappe.session.user}.")
        additional = frappe.get_doc({
            "doctype": "Additional Salary", "employee": row["employee"], "company": doc.company,
            "salary_component": DEDUCTION_COMPONENT, "amount": row["amount"],
            "payroll_date": doc.end_date,
        }).insert(ignore_permissions=True)
        additional.add_comment("Comment", note)  # Additional Salary has no notes field
        additional.submit()
        created.append(additional.name)
    doc.add_comment("Comment", f"{frappe.session.user} applied late and early deductions for {len(created)} people.")
    frappe.db.commit()
    return {"created": len(created), "names": created}
