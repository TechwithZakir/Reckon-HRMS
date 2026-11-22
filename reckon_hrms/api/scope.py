"""One place that keeps every HR and payroll endpoint inside the signed-in person's own company.

A record id sent by the page (a payroll run, an employee, a request) is never trusted: ``own_doc`` and ``own_employee``
refuse a record of another company. Lists and counts use ``mine()``, never a company the page sends.
"""

from __future__ import annotations

import frappe
from frappe import _


def mine() -> str:
    """The signed-in person's own company, resolved by the platform (fails closed without an assignment)."""
    from reckon_hrms.api.home import _company

    return _company()


def _refuse():
    frappe.throw(_("This record belongs to another company."), frappe.PermissionError)


def own_doc(doctype: str, name: str):
    """Load a record, refusing one that belongs to another company."""
    doc = frappe.get_doc(doctype, name)
    owner = doc.get("company")
    if owner and owner != mine():
        _refuse()
    return doc


def own_employee(employee: str) -> str:
    """An employee of the signed-in company, else refused."""
    owner = frappe.db.get_value("Employee", employee, "company")
    if owner != mine():
        _refuse()
    return employee


def shared_or_own(doctype: str) -> dict:
    """Filters for a shared catalog (components, branches...): this company's own and the vendor's standard ones, never another company's."""
    return {"company": ["in", [mine(), "", None]]} if frappe.get_meta(doctype).has_field("company") else {}
