"""Self-service requests and approvals for leave and expense claims.

Employees see their own requests. Approvers see requests routed to them (leave approver or expense
approver) and HR managers see every open request in their company. Every decision runs as the caller,
so Frappe's own permission checks still apply.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from reckon_hrms.api.attendance import _my_employee

DECIDABLE = ("Leave Application", "Expense Claim")


def _lists_for(doctype: str):
    return {
        "Leave Application": ("name", "employee_name", "leave_type", "from_date", "to_date", "status", "docstatus"),
        "Expense Claim": ("name", "employee_name", "expense_approver", "total_claimed_amount",
                          "approval_status", "posting_date", "docstatus"),
    }[doctype]


@frappe.whitelist(methods=["GET"])
def my_requests() -> dict:
    employee = _my_employee()
    leaves = frappe.get_all("Leave Application", filters={"employee": employee.name},
                            fields=list(_lists_for("Leave Application")), order_by="creation desc", limit=20)
    claims = frappe.get_all("Expense Claim", filters={"employee": employee.name},
                            fields=list(_lists_for("Expense Claim")), order_by="creation desc", limit=20)
    return {"leaves": leaves, "claims": claims}


@frappe.whitelist(methods=["GET"])
def inbox() -> dict:
    """Open requests this user can decide. Each row is limited by Frappe's own permission checks."""
    user = frappe.session.user
    leaves = frappe.get_list(
        "Leave Application",
        filters={"status": "Open", "docstatus": 0},
        or_filters={"leave_approver": user},
        fields=list(_lists_for("Leave Application")), order_by="creation asc", limit_page_length=50,
    )
    claims = frappe.get_list(
        "Expense Claim",
        filters={"docstatus": 0, "approval_status": ["in", ["Draft", "Pending"]]},
        or_filters={"expense_approver": user},
        fields=list(_lists_for("Expense Claim")), order_by="creation asc", limit_page_length=50,
    )
    return {"leaves": leaves, "claims": claims, "count": len(leaves) + len(claims)}


@frappe.whitelist(methods=["POST"])
def decide(doctype: str, name: str, decision: str, amount: float | None = None, remark: str | None = None) -> dict:
    if doctype not in DECIDABLE:
        frappe.throw(_("This request type cannot be approved here."))
    if decision not in ("Approve", "Reject"):
        frappe.throw(_("Choose Approve or Reject."))

    doc = frappe.get_doc(doctype, name)
    if not frappe.has_permission(doctype, "submit", doc):
        frappe.throw(_("You are not allowed to decide this request."), frappe.PermissionError)
    if doc.docstatus != 0:
        frappe.throw(_("This request has already been decided."))

    approved = decision == "Approve"
    if doctype == "Leave Application":
        doc.status = "Approved" if approved else "Rejected"
    else:
        claimed = flt(doc.total_claimed_amount)
        sanctioned = flt(amount) if amount not in (None, "") else claimed
        if approved and (sanctioned <= 0 or sanctioned > claimed):
            frappe.throw(_("Sanctioned amount must be between 0 and the claimed amount."))
        doc.approval_status = "Approved" if approved else "Rejected"
        doc.total_sanctioned_amount = sanctioned if approved else 0
    if remark:
        doc.add_comment("Comment", remark)
    doc.submit()
    return {"doctype": doctype, "name": doc.name, "decision": decision}
