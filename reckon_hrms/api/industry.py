"""Industry onboarding and salary suggestions: list segments, choose one, suggest a band."""

from __future__ import annotations

import frappe
from frappe import _

from reckon_hrms import industry_seed, salary_suggest
from reckon_hrms.api.home import _company

ADMIN_ROLES = ["HR Manager", "System Manager"]
PAY_ROLES = ["HR Manager", "Payroll Manager", "System Manager"]


@frappe.whitelist(methods=["GET"])
def list_segments() -> list[dict]:
    frappe.only_for(ADMIN_ROLES + ["Payroll Manager"])
    return salary_suggest.segments()


@frappe.whitelist(methods=["POST"])
def choose_segment(segment: str) -> dict:
    """Seed the signed-in company's starter masters for the chosen segment. Repeat calls are safe."""
    frappe.only_for(ADMIN_ROLES)
    if not frappe.has_permission("Company", "write"):
        frappe.throw(_("You do not have permission to change this company's setup."), frappe.PermissionError)
    company = _company()
    result = industry_seed.apply_segment(company, segment)
    frappe.db.commit()
    return result


@frappe.whitelist(methods=["GET"])
def suggest_salary(segment: str, role: str, current_gross: float | None = None) -> dict:
    """Band for a role with confidence and caveats. Pay data, so only payroll and HR roles see it."""
    frappe.only_for(PAY_ROLES)
    return salary_suggest.suggest(segment, role, current_gross=current_gross)
