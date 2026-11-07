"""Reckon HRMS registration in reckon_saas_platform (``reckon_saas_modules`` hook)."""

from __future__ import annotations

from reckon_hrms.constants import (
    ADMIN_ROLE,
    DESK_DOCTYPES,
    DESK_GUARD,
    DESK_WORKSPACES,
    HOME_ROUTE,
    MODULE_FEATURES,
    MODULE_KEY,
    MODULE_LABEL,
    ROLES,
    TENANT_OWNED_DOCTYPES,
    WORKSPACE,
)


def get_module_definition() -> dict:
    return {
        "key": MODULE_KEY,
        "label": MODULE_LABEL,
        "description": "Compact HR and payroll for small businesses: employees, "
        "attendance and shifts, leave and payroll, one Company per tenant.",
        "workspace": WORKSPACE,
        "home_route": HOME_ROUTE,
        "admin_role": ADMIN_ROLE,
        "roles": list(ROLES),
        "seed_handler": "reckon_hrms.seed.run_hrms_seed",
        "subscription_features": list(MODULE_FEATURES),
        "desk_guard": DESK_GUARD,
        "desk_doctypes": list(DESK_DOCTYPES),
        "desk_workspaces": list(DESK_WORKSPACES),
        # The platform creates per-company roles and reconciles team access for these.
        "tenant_role_prefix": "Reckon HRMS",
        "tenant_doctypes": list(TENANT_OWNED_DOCTYPES),
        # Company admins get full rights on the company's records through the per-company admin role.
        "tenant_grants": {
            "Admin": {"read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1},
            "User": {},
        },
        # Module roles a team member can be given. They map onto Frappe HRMS roles (shared).
        "tenant_role_map": {
            "HR Manager": "HR Manager",
            "Payroll Manager": "Payroll Manager",
            "Talent Admin": "Interviewer",
            "Employee Self Service": "Employee Self Service",
        },
        "tenant_admin_map": "HR Manager",
        "tenant_default_role": "Employee Self Service",
    }
