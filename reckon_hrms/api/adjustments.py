"""Changes to one pay component for one person in a run, with a reason and an approval.

Any component can be changed (pay items, deductions and gross). A request holds the new amount for that
component. It is saved as a draft Additional Salary with "overwrite salary structure amount" on, so
HRMS uses this amount on the slip instead of the structure amount. A Payroll Manager who did not make the
request approves it: the earlier approved value for that component is cancelled and this one is submitted.
Nothing changes on a slip until it is approved, and requests stop once salary slips exist.

Gross is changed through Basic Salary: the difference is put on basic pay, because the other pay items
are worked out from the structure's formulas.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

REQUEST_ROLES = ["HR Manager", "Payroll Manager", "System Manager"]
APPROVE_ROLES = ["Payroll Manager", "System Manager"]


def _run(name: str):
    doc = frappe.get_doc("Payroll Entry", name)
    if doc.docstatus != 0:
        frappe.throw(_("This run is no longer a draft."))
    return doc


@frappe.whitelist(methods=["POST"])
def request_change(name: str, employee: str, component: str, amount: float, reason: str) -> dict:
    """Ask for a new amount for one component of one person in this run. Waits for a Payroll Manager."""
    frappe.only_for(REQUEST_ROLES)
    amount = flt(amount)
    if amount < 0:
        frappe.throw(_("The amount cannot be negative."))
    reason = (reason or "").strip()
    if not reason:
        frappe.throw(_("Give a reason for the change."))
    doc = _run(name)
    if frappe.db.exists("Salary Slip", {"payroll_entry": name, "docstatus": ["!=", 2]}):
        frappe.throw(_("Salary slips already exist. Ask for the change before slips are created."))
    if employee not in [r.employee for r in doc.employees]:
        frappe.throw(_("This person is not on this run."))
    if not frappe.db.exists("Salary Component", component):
        frappe.throw(_("Unknown pay item: {0}").format(component))

    # A newer request for the same person and component replaces the waiting one.
    for old in frappe.get_all("Additional Salary", filters={
            "employee": employee, "salary_component": component, "docstatus": 0,
            "payroll_date": doc.end_date}, pluck="name"):
        frappe.delete_doc("Additional Salary", old, ignore_permissions=True)

    request = frappe.get_doc({
        "doctype": "Additional Salary", "employee": employee, "company": doc.company,
        "salary_component": component, "amount": amount, "payroll_date": doc.end_date,
        "overwrite_salary_structure_amount": 1,
    }).insert(ignore_permissions=True)
    # Additional Salary has no notes field, so the reason is kept as a comment on the request.
    request.add_comment("Comment", f"Run {name}: {reason}. Requested by {frappe.session.user}.")
    doc.add_comment("Comment", f"{frappe.session.user} requested {component} of {amount:,.2f} for {employee}: {reason}.")
    frappe.db.commit()
    return {"name": request.name, "status": "Pending approval"}


@frappe.whitelist(methods=["GET"])
def pending_requests(name: str) -> list[dict]:
    """Changes for this run waiting for approval."""
    frappe.only_for(REQUEST_ROLES)
    doc = frappe.get_doc("Payroll Entry", name)
    people = [r.employee for r in doc.employees]
    if not people:
        return []
    rows = frappe.get_all("Additional Salary", filters={
        "employee": ["in", people], "docstatus": 0, "company": doc.company,
        "payroll_date": doc.end_date},
        fields=["name", "employee", "employee_name", "salary_component", "amount", "owner"],
        order_by="creation asc", limit_page_length=0)
    reasons = _first_comments("Additional Salary", [r.name for r in rows])
    return [{**r, "notes": reasons.get(r.name, ""), "requested_by": r.owner,
             "can_decide": r.owner != frappe.session.user} for r in rows]


@frappe.whitelist(methods=["POST"])
def approve_request(request: str) -> dict:
    """A Payroll Manager approves a change: the earlier approved value is cancelled and this one submitted."""
    frappe.only_for(APPROVE_ROLES)
    doc = frappe.get_doc("Additional Salary", request)
    if doc.docstatus != 0:
        frappe.throw(_("This request is already decided."))
    if doc.owner == frappe.session.user:
        frappe.throw(_("Someone else must approve this request. You made it."))
    if frappe.db.exists("Salary Slip", {"payroll_entry": _run_for(doc), "docstatus": ["!=", 2]}):
        frappe.throw(_("Salary slips already exist for this run."))
    if doc.overwrite_salary_structure_amount:
        for earlier in frappe.get_all("Additional Salary", filters={
                "employee": doc.employee, "salary_component": doc.salary_component, "docstatus": 1,
                "payroll_date": doc.payroll_date}, pluck="name"):
            frappe.get_doc("Additional Salary", earlier).cancel()
    doc.submit()
    frappe.db.commit()
    return {"name": doc.name, "status": "Approved"}


@frappe.whitelist(methods=["POST"])
def reject_request(request: str, reason: str | None = None) -> dict:
    """A Payroll Manager rejects a change. The waiting request is removed."""
    frappe.only_for(APPROVE_ROLES)
    doc = frappe.get_doc("Additional Salary", request)
    if doc.docstatus != 0:
        frappe.throw(_("This request is already decided."))
    if doc.owner == frappe.session.user:
        frappe.throw(_("Someone else must decide this request. You made it."))
    doc.add_comment("Comment", f"{frappe.session.user} rejected this request. {reason or ''}".strip())
    doc.delete(ignore_permissions=True)
    frappe.db.commit()
    return {"name": request, "status": "Rejected"}


def _first_comments(doctype: str, names: list[str]) -> dict[str, str]:
    """The first comment on each record (its reason), keyed by record name."""
    if not names:
        return {}
    found: dict[str, str] = {}
    for row in frappe.get_all("Comment", filters={"reference_doctype": doctype, "reference_name": ["in", names],
                                                  "comment_type": "Comment"},
                              fields=["reference_name", "content"], order_by="creation asc", limit_page_length=0):
        found.setdefault(row.reference_name, row.content)
    return found


def _run_for(additional) -> str | None:
    """The draft run this request belongs to: a draft that lists the person and covers the request's date."""
    runs = frappe.get_all("Payroll Employee Detail", filters={"employee": additional.employee,
                                                             "parenttype": "Payroll Entry"}, pluck="parent")
    for run in runs:
        row = frappe.db.get_value("Payroll Entry", run, ["docstatus", "end_date"], as_dict=True)
        if row and row.docstatus == 0 and str(row.end_date) >= str(additional.payroll_date):
            return run
    return None
