"""Reckon HRMS tenant access. Delegates to the platform, which owns team and role reconciliation.

Kept so existing callers (the seed) keep working; the logic lives in reckon_saas_platform.team.
"""

from __future__ import annotations

import frappe

from reckon_saas_platform.team import ensure_tenant_roles as _ensure_tenant_roles
from reckon_saas_platform.team import reconcile_user as _reconcile_user
from reckon_saas_platform.team import sync_tenant_user_access as _sync_tenant_user_access

from reckon_hrms.saas_module import get_module_definition


def ensure_tenant_roles(company: str) -> dict:
    return _ensure_tenant_roles(get_module_definition(), company)


def reconcile_user(user: str) -> None:
    _reconcile_user(user)


def apply_assignment(user: str, company: str, role_profile: str | None) -> None:
    _reconcile_user(user)


def sync_tenant_user_access(doc, method=None) -> None:
    _sync_tenant_user_access(doc, method)


ESS_ROLE = "Employee Self Service"


def _set_self_service(user: str, employee: str | None, wants: bool) -> None:
    """Self-service users see only their own employee record (and records linked to it)."""
    existing = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": "Employee", "apply_to_all_doctypes": 1},
        fields=["name", "for_value"],
    )
    if wants and employee:
        for row in existing:
            if row.for_value != employee:
                frappe.delete_doc("User Permission", row.name, ignore_permissions=True, force=True)
        if not any(row.for_value == employee for row in existing):
            frappe.get_doc({
                "doctype": "User Permission", "user": user, "allow": "Employee", "for_value": employee,
                "apply_to_all_doctypes": 1, "is_default": 0,
            }).insert(ignore_permissions=True)
    else:
        for row in existing:
            frappe.delete_doc("User Permission", row.name, ignore_permissions=True, force=True)


def sync_self_service(doc, method=None) -> None:
    """Tenant User Assignment hook: self-service scope follows the assignment's module role."""
    user, company = doc.get("user"), doc.get("company")
    if not user or not company or user in {"Guest", "Administrator"}:
        return
    employee = frappe.db.get_value("Employee", {"user_id": user, "company": company}, "name")
    wants = bool(doc.get("active")) and doc.get("module_role") == ESS_ROLE
    caller = frappe.session.user
    frappe.set_user("Administrator")
    try:
        _set_self_service(user, employee, wants)
    finally:
        frappe.set_user(caller)


def sync_employee_self_service(doc, method=None) -> None:
    """Employee hook: when a linked login is self-service, scope it to this record."""
    user = doc.get("user_id")
    if not user:
        return
    assignments = frappe.get_all(
        "Tenant User Assignment",
        filters={"user": user, "company": doc.get("company"), "active": 1},
        fields=["module_role"],
    )
    wants = any(row.module_role == ESS_ROLE for row in assignments)
    caller = frappe.session.user
    frappe.set_user("Administrator")
    try:
        _set_self_service(user, doc.name, wants)
    finally:
        frappe.set_user(caller)
