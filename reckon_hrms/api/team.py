"""Company team management for Reckon HRMS. Delegates to the platform's team endpoints."""

from __future__ import annotations

import frappe
from reckon_saas_platform.team import add_team_member, list_team_members, remove_team_member


@frappe.whitelist(methods=["GET"])
def list_members() -> list[dict]:
    return list_team_members()


@frappe.whitelist(methods=["POST"])
def add_member(email: str, full_name: str | None = None, role_profile: str = "Company Manager") -> dict:
    return add_team_member(email, full_name, role_profile)


@frappe.whitelist(methods=["POST"])
def remove_member(email: str) -> dict:
    return remove_team_member(email)
