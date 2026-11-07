"""Tenant seed for Reckon HRMS: company roles, permissions, and assignment of existing users.

Runs once per tenant Company. Adds no business data.
"""

from __future__ import annotations

import frappe

from reckon_hrms.access import apply_assignment, ensure_tenant_roles


def run_hrms_seed(company: str, seed_version: str) -> dict:
    roles = ensure_tenant_roles(company)
    assignees = frappe.get_all(
        "Tenant User Assignment", filters={"company": company, "active": 1},
        fields=["user", "role_profile"],
    )
    for row in assignees:
        apply_assignment(row.user, company, row.role_profile)
    frappe.clear_cache()
    return {"company": company, "seed_version": seed_version, "roles": list(roles.values()),
            "assigned": sorted({r.user for r in assignees})}
