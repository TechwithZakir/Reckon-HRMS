"""Company team management for Reckon HRMS. The company always comes from the caller's assignment."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import validate_email_address

ALLOWED_PROFILES = ("Company Manager", "Company Admin")


def _admin_company() -> str:
    """The caller's single active company where they are Company Admin."""
    user = frappe.session.user
    if user in {"Guest", "Administrator"}:
        frappe.throw(_("Sign in as a company admin."), frappe.PermissionError)
    companies = frappe.get_all(
        "Tenant User Assignment",
        filters={"user": user, "active": 1, "role_profile": "Company Admin"},
        pluck="company",
    )
    if len(companies) != 1:
        frappe.throw(_("Only a company admin of one company can manage the team."), frappe.PermissionError)
    return companies[0]


@frappe.whitelist(methods=["GET"])
def list_members() -> list[dict]:
    company = _admin_company()
    return frappe.get_all(
        "Tenant User Assignment",
        filters={"company": company, "active": 1},
        fields=["user", "role_profile"],
        order_by="creation asc",
    )


@frappe.whitelist(methods=["POST"])
def add_member(email: str, full_name: str | None = None, role_profile: str = "Company Manager") -> dict:
    company = _admin_company()
    email = (email or "").strip().lower()
    if not validate_email_address(email):
        frappe.throw(_("Enter a valid email address."))
    if role_profile not in ALLOWED_PROFILES:
        frappe.throw(_("Unknown role profile."))
    other = frappe.get_all(
        "Tenant User Assignment",
        filters={"user": email, "active": 1, "company": ["!=", company]},
        pluck="company",
    )
    if other:
        frappe.throw(_("This user already belongs to another company."))

    if not frappe.db.exists("User", email):
        frappe.get_doc({
            "doctype": "User", "email": email, "first_name": full_name or email,
            "enabled": 1, "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
    existing = frappe.db.get_value("Tenant User Assignment", {"user": email, "company": company}, "name")
    if existing:
        doc = frappe.get_doc("Tenant User Assignment", existing)
        doc.db_set({"active": 1, "role_profile": role_profile})
        doc.reload()
    else:
        doc = frappe.get_doc({
            "doctype": "Tenant User Assignment", "user": email, "company": company,
            "role_profile": role_profile, "active": 1, "is_default": 1,
        }).insert(ignore_permissions=True)
    return {"user": email, "company": company, "role_profile": role_profile, "assignment": doc.name}


@frappe.whitelist(methods=["POST"])
def remove_member(email: str) -> dict:
    company = _admin_company()
    email = (email or "").strip().lower()
    if email == frappe.session.user:
        frappe.throw(_("You cannot remove yourself."))
    name = frappe.db.get_value("Tenant User Assignment", {"user": email, "company": company, "active": 1}, "name")
    if not name:
        frappe.throw(_("This user is not on your team."))
    frappe.db.set_value("Tenant User Assignment", name, "active", 0)
    frappe.get_doc("Tenant User Assignment", name).run_method("on_update")
    return {"user": email, "company": company, "removed": True}
