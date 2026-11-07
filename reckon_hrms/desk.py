"""Desk entry points for Reckon HRMS."""

from __future__ import annotations

import frappe

from reckon_hrms.constants import ADMIN_ROLE, ROLES


def can_see_app() -> bool:
    """The Reckon HRMS tile shows for Administrators and for users with an HRMS role."""
    user = frappe.session.user
    if user in {"Guest"}:
        return False
    if user == "Administrator":
        return True
    roles = set(frappe.get_roles(user))
    return bool(roles & (set(ROLES) | {ADMIN_ROLE})) or any(
        role.startswith("Reckon HRMS ") and " - " in role for role in roles
    )
