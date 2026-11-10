"""Edits to a run's totals (more additions or deductions for one person) go through approval.

An HR user requests an increase: it is saved as a draft Additional Salary (not paid yet). A Payroll
Manager who did not make the request approves it, which submits it so it lands on the slip. Only
increases are requested here: a lower amount needs a change to the salary structure, on Salary rules.
Requests are accepted only before salary slips exist, as slips are made from what is approved then.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from reckon_hrms import industry_seed

REQUEST_ROLES = ["HR Manager", "Payroll Manager", "System Manager"]
APPROVE_ROLES = ["Payroll Manager", "System Manager"]
COMPONENTS = {"additions": "Run Adjustment Earning", "deductions": "Run Adjustment Deduction"}


def _run(name: str):
    doc = frappe.get_doc("Payroll Entry", name)
    if doc.docstatus != 0:
        frappe.throw(_("This run is no longer a draft."))
    return doc


@frappe.whitelist(methods=["POST"])
def request_increase(name: str, employee: str, kind: str, amount: float, reason: str) -> dict:
    """Ask for an increase in one person's additions or deductions for this run. Waits for a Payroll Manager."""
    frappe.only_for(REQUEST_ROLES)
    if kind not in COMPONENTS:
        frappe.throw(_("Choose additions or deductions."))
    amount = flt(amount)
    if amount <= 0:
        frappe.throw(_("Only an increase can be requested. A lower amount needs a change to the salary structure."))
    reason = (reason or "").strip()
    if not reason:
        frappe.throw(_("Give a reason for the change."))
    doc = _run(name)
    if frappe.db.exists("Salary Slip", {"payroll_entry": name, "docstatus": ["!=", 2]}):
        frappe.throw(_("Salary slips already exist. Ask for the change before slips are created."))
    if employee not in [r.employee for r in doc.employees]:
        frappe.throw(_("This person is not on this run."))

    component = COMPONENTS[kind]
    industry_seed._component(component)
    industry_seed._ensure_component_account(doc.company, component)
    request = frappe.get_doc({
        "doctype": "Additional Salary", "employee": employee, "company": doc.company,
        "salary_component": component, "amount": amount, "payroll_date": doc.end_date,
        "notes": f"Run {name}: {reason}. Requested by {frappe.session.user}.",
    }).insert(ignore_permissions=True)
    doc.add_comment("Comment", f"{frappe.session.user} requested {kind} of {amount:,.2f} for {employee}: {reason}.")
    frappe.db.commit()
    return {"name": request.name, "status": "Pending approval"}


@frappe.whitelist(methods=["GET"])
def pending_requests(name: str) -> list[dict]:
    """Requests for this run waiting for approval."""
    frappe.only_for(REQUEST_ROLES)
    doc = frappe.get_doc("Payroll Entry", name)
    people = [r.employee for r in doc.employees]
    if not people:
        return []
    rows = frappe.get_all("Additional Salary", filters={
        "employee": ["in", people], "docstatus": 0, "company": doc.company,
        "salary_component": ["in", list(COMPONENTS.values())],
        "payroll_date": ["between", [doc.start_date, doc.end_date]]},
        fields=["name", "employee", "employee_name", "salary_component", "amount", "notes", "owner"],
        order_by="creation asc", limit_page_length=0)
    return [{**r, "kind": "additions" if r.salary_component == COMPONENTS["additions"] else "deductions",
             "requested_by": r.owner, "can_decide": r.owner != frappe.session.user} for r in rows]


@frappe.whitelist(methods=["POST"])
def approve_request(request: str) -> dict:
    """A Payroll Manager approves a request, which submits it. Nobody approves their own request."""
    frappe.only_for(APPROVE_ROLES)
    doc = frappe.get_doc("Additional Salary", request)
    if doc.docstatus != 0:
        frappe.throw(_("This request is already decided."))
    if doc.owner == frappe.session.user:
        frappe.throw(_("Someone else must approve this request. You made it."))
    if frappe.db.exists("Salary Slip", {"payroll_entry": _run_for(doc), "docstatus": ["!=", 2]}):
        frappe.throw(_("Salary slips already exist for this run."))
    doc.submit()
    frappe.db.commit()
    return {"name": doc.name, "status": "Approved"}


@frappe.whitelist(methods=["POST"])
def reject_request(request: str, reason: str | None = None) -> dict:
    """A Payroll Manager rejects a request. It is kept in the record as cancelled."""
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


def _run_for(additional) -> str | None:
    """The run a request belongs to, read from its notes (Run <name>: ...)."""
    notes = additional.get("notes") or ""
    if notes.startswith("Run "):
        return notes[4:].split(":", 1)[0].strip()
    return None
