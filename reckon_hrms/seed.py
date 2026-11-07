"""Tenant seed for Reckon HRMS: company roles, starter masters, and assignment of existing users.

Runs once per tenant Company. Creates generic starter masters only (see reckon_hrms.defaults),
never another tenant's business data. Every step is idempotent.
"""

from __future__ import annotations

import frappe

from reckon_hrms.access import apply_assignment, ensure_tenant_roles
from reckon_hrms.defaults import DEPARTMENTS, DESIGNATIONS, LEAVE_TYPES, SALARY_COMPONENTS, SHIFT_TYPES


def ensure_shared_defaults() -> dict:
    """Shared masters (no Company field): created once, reused by every tenant."""
    created = {"shift_types": 0, "leave_types": 0, "salary_components": 0, "designations": 0}
    for row in SHIFT_TYPES:
        if not frappe.db.exists("Shift Type", row["name"]):
            frappe.get_doc({"doctype": "Shift Type", "name": row["name"], "start_time": row["start_time"],
                            "end_time": row["end_time"]}).insert(ignore_permissions=True)
            created["shift_types"] += 1
    for row in LEAVE_TYPES:
        if not frappe.db.exists("Leave Type", row["name"]):
            frappe.get_doc({"doctype": "Leave Type", "leave_type_name": row["name"],
                            "max_leaves_allowed": row["max_leaves_allowed"]}).insert(ignore_permissions=True)
            created["leave_types"] += 1
    for row in SALARY_COMPONENTS:
        if not frappe.db.exists("Salary Component", row["name"]):
            frappe.get_doc({"doctype": "Salary Component", "salary_component": row["name"],
                            "salary_component_abbr": row["abbr"], "type": row["type"]}).insert(ignore_permissions=True)
            created["salary_components"] += 1
    for name in DESIGNATIONS:
        if not frappe.db.exists("Designation", name):
            frappe.get_doc({"doctype": "Designation", "designation_name": name}).insert(ignore_permissions=True)
            created["designations"] += 1
    return created


def ensure_company_defaults(company: str) -> dict:
    """Company-owned starter masters: departments and a holiday calendar for each tenant."""
    created = 0
    for name in DEPARTMENTS:
        if not frappe.db.exists("Department", {"department_name": name, "company": company}):
            frappe.get_doc({"doctype": "Department", "department_name": name, "company": company}).insert(
                ignore_permissions=True
            )
            created += 1
    holiday_list = f"Standard Holidays - {company}"[:140]
    holiday_list_created = 0
    if not frappe.db.exists("Holiday List", {"company": company}):
        year = frappe.utils.getdate().year
        frappe.get_doc({
            "doctype": "Holiday List",
            "holiday_list_name": holiday_list,
            "company": company,
            "from_date": f"{year}-01-01",
            "to_date": f"{year}-12-31",
            "weekly_off": "Friday",
        }).insert(ignore_permissions=True)
        holiday_list_created = 1
    return {"departments": created, "holiday_list": holiday_list_created}


def run_hrms_seed(company: str, seed_version: str) -> dict:
    roles = ensure_tenant_roles(company)
    shared = ensure_shared_defaults()
    departments = ensure_company_defaults(company)
    assignees = frappe.get_all(
        "Tenant User Assignment", filters={"company": company, "active": 1},
        fields=["user", "role_profile"],
    )
    for row in assignees:
        apply_assignment(row.user, company, row.role_profile)
    frappe.clear_cache()
    return {"company": company, "seed_version": seed_version, "roles": list(roles.values()),
            "shared_created": shared, "departments_created": departments["departments"],
            "assigned": sorted({r.user for r in assignees})}
