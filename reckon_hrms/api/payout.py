"""Monthly payroll payout: per-employee pay types, additions, deductions, basis and gross payable,
plus bulk custom entries for the selected employees.

Figures come from the month's salary slips where a run has been made. Employees without a slip show
their structure base and any approved additions, marked as not generated.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_months, flt, get_first_day, getdate

from reckon_hrms.api.home import _company

PAYROLL_ROLES = ["HR Manager", "Payroll Manager", "System Manager"]


def _month_bounds(month: str):
    try:
        start = getdate(f"{month}-01")
    except Exception:
        frappe.throw(_("Choose a month as YYYY-MM."))
    return get_first_day(start), get_first_day(add_months(start, 1))


def _company_for(company: str | None) -> str:
    own = _company()
    if company and company != own:
        frappe.throw(_("You can only work with your own company."), frappe.PermissionError)
    return own


@frappe.whitelist(methods=["GET"])
def payout_sheet(month: str, company: str | None = None) -> dict:
    frappe.only_for(PAYROLL_ROLES)
    company = _company_for(company)
    start, next_start = _month_bounds(month)

    employees = frappe.get_all(
        "Employee", filters={"company": company, "status": "Active"},
        fields=["name", "employee_name"], order_by="employee_name asc", limit_page_length=0,
    )
    assignments = {
        a.employee: a for a in frappe.get_all(
            "Salary Structure Assignment", filters={"company": company, "docstatus": 1, "from_date": ["<", next_start]},
            fields=["employee", "base", "salary_structure", "from_date"], order_by="from_date asc", limit_page_length=0,
        )
    }
    slips = {}
    for s in frappe.get_all(
        "Salary Slip", filters={"company": company, "docstatus": ["!=", 2],
                                "start_date": [">=", start], "end_date": ["<", next_start]},
        fields=["name", "employee", "start_date"], order_by="modified desc", limit_page_length=0,
    ):
        slips.setdefault(s.employee, s)  # latest slip per employee

    additions = {}
    for a in frappe.get_all(
        "Additional Salary", filters={"company": company, "docstatus": 1,
                                      "payroll_date": ["between", [start, next_start]]},
        fields=["employee", "salary_component", "amount"], limit_page_length=0,
    ):
        additions.setdefault(a.employee, []).append(a)

    earning_names, deduction_names = [], []
    rows = []
    for emp in employees:
        row = {"employee": emp.name, "employee_name": emp.employee_name, "base": 0, "working_days": 0,
               "payment_days": 0, "earnings": {}, "deductions": {}, "gross": 0, "total_deduction": 0,
               "net": 0, "status": "Not generated", "slip": None}
        slip = slips.get(emp.name)
        if slip:
            doc = frappe.get_doc("Salary Slip", slip.name)
            row.update(status="Generated", slip=doc.name, working_days=flt(doc.total_working_days),
                       payment_days=flt(doc.payment_days), gross=flt(doc.gross_pay),
                       total_deduction=flt(doc.total_deduction), net=flt(doc.net_pay))
            base_row = assignments.get(emp.name)
            row["base"] = flt(base_row.base) if base_row else 0
            for r in doc.earnings:
                row["earnings"][r.salary_component] = flt(r.amount)
                if r.salary_component not in earning_names:
                    earning_names.append(r.salary_component)
            for r in doc.deductions:
                row["deductions"][r.salary_component] = flt(r.amount)
                if r.salary_component not in deduction_names:
                    deduction_names.append(r.salary_component)
        else:
            base_row = assignments.get(emp.name)
            row["base"] = flt(base_row.base) if base_row else 0
            extra = sum(flt(a.amount) for a in additions.get(emp.name, []))
            row["gross"] = row["base"] + extra
            row["net"] = row["gross"]
            for a in additions.get(emp.name, []):
                row["earnings"][a.salary_component] = row["earnings"].get(a.salary_component, 0) + flt(a.amount)
                if a.salary_component not in earning_names:
                    earning_names.append(a.salary_component)
        rows.append(row)

    totals = {"base": 0, "gross": 0, "total_deduction": 0, "net": 0}
    for r in rows:
        for key in totals:
            totals[key] += flt(r[key])

    return {
        "company": company, "month": month, "rows": rows,
        "earning_names": earning_names, "deduction_names": deduction_names,
        "totals": totals,
        "components": frappe.get_all("Salary Component", fields=["name", "type"], order_by="name asc", limit_page_length=0),
    }


@frappe.whitelist(methods=["POST"])
def bulk_custom_entry(employees: list | str, month: str, component: str, amount: float, remarks: str | None = None) -> dict:
    """Add one custom earning or deduction (Additional Salary) to every selected employee for the month."""
    frappe.only_for(PAYROLL_ROLES)
    company = _company()
    if isinstance(employees, str):
        employees = frappe.parse_json(employees)
    if not employees:
        frappe.throw(_("Select at least one employee."))
    if flt(amount) <= 0:
        frappe.throw(_("Enter an amount above zero."))
    if not frappe.db.exists("Salary Component", component):
        frappe.throw(_("Unknown salary component."))
    start, _next = _month_bounds(month)

    valid = set(frappe.get_all("Employee", filters={"company": company, "status": "Active"}, pluck="name",
                               limit_page_length=0))
    created = []
    for emp in employees:
        if emp not in valid:
            frappe.throw(_("Employee {0} is not in your company.").format(emp), frappe.PermissionError)
        doc = frappe.get_doc({
            "doctype": "Additional Salary", "employee": emp, "company": company,
            "salary_component": component, "amount": flt(amount), "payroll_date": start,
            "notes": remarks or "",
        }).insert(ignore_permissions=True)
        doc.submit()
        created.append(doc.name)
    frappe.db.commit()
    return {"created": len(created), "names": created}
