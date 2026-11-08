"""Page 3 (Run salary) back end, steps 1 and 2: choose month and people, then check the list.

Each step is a stage of the standard Payroll Entry, so a run started here can be continued in the desk.
Steps 3 to 5 (slips, approval, payment) come later. Lists are server-paged (max 100 rows).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, get_first_day, get_last_day, getdate

from reckon_hrms.api.home import _company
from reckon_hrms.paging import DEFAULT_PAGE, page_bounds

RUN_ROLES = ["HR Manager", "Payroll Manager", "System Manager"]
FILTER_FIELDS = ("branch", "department", "designation", "grade")


def _gate(doctype: str, ptype: str = "read"):
    frappe.only_for(RUN_ROLES)
    if not frappe.has_permission(doctype, ptype):
        frappe.throw(_("You do not have permission to {0} {1}.").format(ptype, doctype.lower()),
                     frappe.PermissionError)


def _month_bounds(month: str):
    try:
        first = get_first_day(getdate(f"{month}-01"))
    except Exception:
        frappe.throw(_("Choose a month as YYYY-MM."))
    return first, get_last_day(first)


def _has_structure(employee: str, start, end) -> bool:
    return bool(frappe.db.exists("Salary Structure Assignment", {
        "employee": employee, "docstatus": 1, "from_date": ["<=", end]}))


@frappe.whitelist(methods=["POST"])
def start_run(month: str, pay_date: str, branch: str | None = None, department: str | None = None,
              designation: str | None = None, grade: str | None = None) -> dict:
    """Create the draft Payroll Entry for this month, or return the existing draft. Idempotent."""
    _gate("Payroll Entry", "create")
    company = _company()
    start, end = _month_bounds(month)
    existing = frappe.db.get_value("Payroll Entry", {
        "company": company, "start_date": start, "end_date": end, "docstatus": 0}, "name")
    if existing:
        return {"name": existing, "created": False}
    doc = frappe.get_doc({
        "doctype": "Payroll Entry", "company": company, "payroll_frequency": "Monthly",
        "start_date": start, "end_date": end, "posting_date": getdate(pay_date),
        "branch": branch or None, "department": department or None,
        "designation": designation or None, "grade": grade or None,
    })
    doc.insert()
    return {"name": doc.name, "created": True}


@frappe.whitelist(methods=["POST"])
def fetch_employees(name: str) -> dict:
    """Step 2: fill the people list (Get Employees), then report what was found."""
    _gate("Payroll Entry", "write")
    doc = frappe.get_doc("Payroll Entry", name)
    if doc.docstatus != 0:
        frappe.throw(_("This run is no longer a draft."))
    doc.employees = []
    doc.set_employee_details = None  # noqa: keep attribute clean
    found = doc.fill_employee_details() or []
    for row in found:
        doc.append("employees", {"employee": row.get("employee"), "employee_name": row.get("employee_name"),
                                 "branch": row.get("branch"), "designation": row.get("designation"),
                                 "department": row.get("department"), "grade": row.get("grade")})
    doc.save()
    frappe.db.commit()
    return get_run(name)


@frappe.whitelist(methods=["GET"])
def get_run(name: str) -> dict:
    _gate("Payroll Entry", "read")
    doc = frappe.get_doc("Payroll Entry", name)
    people = [r.employee for r in doc.employees]
    start, end = doc.start_date, doc.end_date
    no_structure = [p for p in people if not _has_structure(p, start, end)]
    slips = frappe.db.count("Salary Slip", {"payroll_entry": name, "docstatus": ["!=", 2]}) if people else 0
    step = 1 if not people else (2 if not slips else 3)
    return {
        "name": doc.name, "status": doc.status, "docstatus": doc.docstatus, "step": step,
        "company": doc.company, "month": str(start)[:7], "pay_date": str(doc.posting_date),
        "included": len(people), "no_structure": len(no_structure), "slips": slips,
        "filters": {f: doc.get(f) for f in FILTER_FIELDS},
        "locked": doc.docstatus != 0,
    }


@frappe.whitelist(methods=["GET"])
def list_people(name: str, filter: str = "all", search: str | None = None, start=0,
                page_length=DEFAULT_PAGE) -> dict:
    """The people table: paged, filtered on the server. Included means "in this run's list"."""
    _gate("Payroll Entry", "read")
    doc = frappe.get_doc("Payroll Entry", name)
    start_i, length_i = page_bounds(start, page_length)
    rows = []
    for r in doc.employees:
        has = _has_structure(r.employee, doc.start_date, doc.end_date)
        status = "ready" if has else "no_structure"
        if filter == "no_structure" and has:
            continue
        if search:
            text = f"{r.employee} {r.employee_name or ''}".lower()
            if search.lower() not in text:
                continue
        rows.append({"employee": r.employee, "employee_name": r.employee_name, "branch": r.branch,
                     "department": r.department, "designation": r.designation, "status": status,
                     "included": True})
    total = len(rows)
    return {"rows": rows[start_i:start_i + length_i], "total": total, "start": start_i,
            "page_length": length_i}


@frappe.whitelist(methods=["POST"])
def exclude_people(name: str, employees: list | str) -> dict:
    """Step 2 only: take people out of the run's list. No slip exists yet, so nothing else changes."""
    _gate("Payroll Entry", "write")
    if isinstance(employees, str):
        employees = frappe.parse_json(employees)
    doc = frappe.get_doc("Payroll Entry", name)
    if doc.docstatus != 0:
        frappe.throw(_("This run is no longer a draft."))
    if doc.salary_slips_created:
        frappe.throw(_("Salary slips already exist. Leave people out at the next steps."))
    before = len(doc.employees)
    drop = set(employees or [])
    doc.employees = [r for r in doc.employees if r.employee not in drop]
    doc.save()
    frappe.db.commit()
    return {"removed": before - len(doc.employees), "included": len(doc.employees)}


@frappe.whitelist(methods=["POST"])
def include_people(name: str, employees: list | str) -> dict:
    """Step 2 only: put back people who were left out. Uses the standard employee master data."""
    _gate("Payroll Entry", "write")
    if isinstance(employees, str):
        employees = frappe.parse_json(employees)
    doc = frappe.get_doc("Payroll Entry", name)
    if doc.docstatus != 0:
        frappe.throw(_("This run is no longer a draft."))
    present = {r.employee for r in doc.employees}
    added = 0
    for emp in employees or []:
        if emp in present:
            continue
        row = frappe.db.get_value("Employee", {"name": emp, "company": doc.company, "status": "Active"},
                                  ["employee_name", "branch", "department", "designation", "grade"], as_dict=True)
        if not row:
            continue
        doc.append("employees", {"employee": emp, "employee_name": row.employee_name, "branch": row.branch,
                                 "department": row.department, "designation": row.designation, "grade": row.grade})
        added += 1
    doc.save()
    frappe.db.commit()
    return {"added": added, "included": len(doc.employees)}
