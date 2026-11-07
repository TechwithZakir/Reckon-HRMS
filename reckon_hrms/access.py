"""Tenant access sync for Reckon HRMS: per-tenant role, Company permission, shared-role cleanup.

Runs from the Tenant User Assignment hooks, so every assignment (onboarding, team
changes, edits) gets the same access. Idempotent.
"""

from __future__ import annotations

import frappe

from reckon_hrms.constants import ADMIN_ROLE, ROLES, TENANT_OWNED_DOCTYPES, tenant_role

SHARED_ROLES = tuple(ROLES)
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
        if company in have:
            continue
        frappe.get_doc({
            "doctype": "User Permission", "user": user, "allow": "Company", "for_value": company,
            "apply_to_all_doctypes": 1, "is_default": 1,
        }).insert(ignore_permissions=True)


def apply_assignment(user: str, company: str, role_profile: str | None) -> None:
    """Give the user this company's HRMS role and permission, and drop the shared roles."""
    if not frappe.db.exists("User", user) or user in {"Guest", "Administrator"}:
        return
    roles = ensure_tenant_roles(company)
    kind = "Admin" if role_profile == "Company Admin" else "User"
    target = roles[kind]
    doc = frappe.get_doc("User", user)
    current = frappe.get_roles(user)
    if target not in current:
        doc.add_roles(target)
    for shared in SHARED_ROLES:
        if shared in current:
            doc.remove_roles(shared)
    companies = frappe.get_all("Tenant User Assignment", filters={"user": user, "active": 1}, pluck="company")
    sync_company_permission(user, sorted(set(companies)))
    frappe.clear_cache(user=user)


def sync_tenant_user_access(doc, method=None) -> None:
    """Tenant User Assignment hook. Only assignments for HRMS-subscribed companies."""
    from reckon_saas_platform.saas import is_subscription_active

    if not doc.get("active") or not doc.get("user") or not doc.get("company"):
        return
    if not is_subscription_active(doc.company, "hrms"):
        return
    apply_assignment(doc.user, doc.company, doc.get("role_profile"))
