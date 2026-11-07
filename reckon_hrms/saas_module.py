"""Reckon HRMS registration in reckon_saas_platform (``reckon_saas_modules`` hook)."""

from __future__ import annotations

from reckon_hrms.constants import (
    ADMIN_ROLE,
    HOME_ROUTE,
    MODULE_FEATURES,
    MODULE_KEY,
    MODULE_LABEL,
    ROLES,
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
    }
