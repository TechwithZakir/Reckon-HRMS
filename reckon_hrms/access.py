"""Tenant access for Reckon HRMS: per-company roles, Company permissions, reconciled per user.

A user's Reckon HRMS roles always match their active assignments in HRMS-subscribed
companies. Adding, changing or deactivating an assignment reconciles the whole set.
"""

from __future__ import annotations

import frappe

from reckon_hrms.constants import ADMIN_ROLE, ROLES, TENANT_OWNED_DOCTYPES, tenant_role

SHARED_ROLES = tuple(ROLES)
MODULE_ROLE_PREFIX = "Reckon HRMS "
GRANTS = {
    "Admin": {"read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1},
    "User": {"read": 1, "write": 1, "create": 1},
}


def ensure_tenant_roles(company: str) -> dict:
    """Create the company's roles and their permissions on the HRMS doctypes."""
    roles = {}
    for kind, flags in GRANTS.items():
        role = tenant_role(kind, company)
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
        for doctype in TENANT_OWNED_DOCTYPES:
            if not frappe.db.exists("DocType", doctype):
                continue
            if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
                continue
            frappe.get_doc({
                "doctype": "Custom DocPerm", "parent": doctype, "parenttype": "DocType",
                "parentfield": "permissions", "role": role, "permlevel": 0,
                **{k: flags.get(k, 0) for k in ("read", "write", "create", "delete", "submit", "cancel")},
            }).insert(ignore_permissions=True)
        roles[kind] = role
    return roles


def sync_company_permission(user: str, companies: list[str]) -> None:
    """Exactly one standard Company User Permission per active company, none for others."""
    existing = frappe.get_all(
        "User Permission", filters={"user": user, "allow": "Company"}, fields=["name", "for_value"]
    )
    for row in existing:
        if row.for_value not in companies:
            frappe.delete_doc("User Permission", row.name, ignore_permissions=True, force=True)
    have = {row.for_value for row in existing if row.for_value in companies}
    for company in companies:
        if company not in have:
            frappe.get_doc({
                "doctype": "User Permission", "user": user, "allow": "Company", "for_value": company,
                "apply_to_all_doctypes": 1, "is_default": 1,
            }).insert(ignore_permissions=True)


def reconcile_user(user: str) -> None:
    """Make the user's Reckon HRMS roles and Company permissions match their active assignments.

    Role changes are server-side work, so they run as Administrator even when a company
    admin triggered them; the caller's session is restored afterwards.
    """
    caller = frappe.session.user
    frappe.set_user("Administrator")
    try:
        _reconcile(user)
    finally:
        frappe.set_user(caller)


def _reconcile(user: str) -> None:
    from reckon_saas_platform.saas import is_subscription_active

    if not user or user in {"Guest", "Administrator"} or not frappe.db.exists("User", user):
        return
    rows = frappe.get_all(
        "Tenant User Assignment", filters={"user": user, "active": 1}, fields=["company", "role_profile"]
    )
    desired, companies = set(), []
    for row in rows:
        if not is_subscription_active(row.company, "hrms"):
            continue
        roles = ensure_tenant_roles(row.company)
        desired.add(roles["Admin"] if row.role_profile == "Company Admin" else roles["User"])
        companies.append(row.company)

    module_roles = set(frappe.get_all("Role", filters={"name": ["like", MODULE_ROLE_PREFIX + "%"]}, pluck="name"))
    module_roles = {r for r in module_roles if " - " in r}
    doc = frappe.get_doc("User", user)
    current = set(frappe.get_roles(user))
    for role in sorted(desired - current):
        doc.add_roles(role)
    for role in sorted(((module_roles | set(SHARED_ROLES)) & current) - desired):
        doc.remove_roles(role)
    sync_company_permission(user, sorted(set(companies)))
    frappe.clear_cache(user=user)


def apply_assignment(user: str, company: str, role_profile: str | None) -> None:
    """Kept for the seed; the reconcile covers every assignment the user has."""
    reconcile_user(user)


def sync_tenant_user_access(doc, method=None) -> None:
    """Tenant User Assignment hook: reconcile the user, including when an assignment is deactivated."""
    if doc.get("user"):
        reconcile_user(doc.user)
