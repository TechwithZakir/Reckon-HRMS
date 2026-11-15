"""doc_events wrappers for the platform's tenant functions.

Frappe calls doc_events hooks as ``hook(doc, method)``. The platform functions take
``user`` as their second argument, so passing them directly would treat the event
name as a user. These wrappers pass the session user explicitly.
"""

import frappe

from reckon_saas_platform.tenant_security import (
    bind_doc_to_tenant,
    validate_tenant_company_immutable,
    validate_tenant_owned_doc,
)


def bind_company(doc, method=None, *args, **kwargs):
    bind_doc_to_tenant(doc, user=frappe.session.user)


def bind_catalog_company(doc, method=None, *args, **kwargs):
    """A tenant's own Leave Type, Designation and the like carry its company; the vendor's stay shared."""
    from reckon_saas_platform.tenant_security import tenant_company_or_none

    company = tenant_company_or_none(frappe.session.user)
    if company and doc.is_new() and not doc.get("company"):
        doc.company = company
    elif company and doc.get("company") and doc.company != company:
        frappe.throw(frappe._("This record belongs to another company."), frappe.PermissionError)


def validate_company_immutable(doc, method=None, *args, **kwargs):
    validate_tenant_company_immutable(doc)


def validate_owned(doc, method=None, *args, **kwargs):
    validate_tenant_owned_doc(doc, user=frappe.session.user)


# ---------- rows reached through another record ----------

def _tenant_company():
    from reckon_saas_platform.tenant_security import TenantResolutionError, require_tenant, user_can_bypass_tenant

    if user_can_bypass_tenant(frappe.session.user):
        return None, True
    try:
        return require_tenant(user=frappe.session.user).company, False
    except TenantResolutionError:
        return None, False


def holiday_assignment_query(user=None, doctype=None):
    """Holiday List Assignment has no Company: it belongs to the company of the Holiday List it assigns."""
    company, bypass = _tenant_company()
    if bypass:
        return ""
    if not company:
        return "1=0"
    return (
        "`tabHoliday List Assignment`.`holiday_list` in "
        f"(select `name` from `tabHoliday List` where `company` = {frappe.db.escape(company)})"
    )


def holiday_assignment_permission(doc, user=None, permission_type=None, ptype=None, **_ignored):
    permission_type = permission_type or ptype  # Frappe passes the right as ptype
    company, bypass = _tenant_company()
    if bypass:
        return True
    if not company:
        return False
    return bool(doc.get("holiday_list")) and frappe.db.get_value("Holiday List", doc.holiday_list, "company") == company


def employee_linked_query(user=None, doctype=None):
    """Employee Checkin (and other rows that only name an employee) belong to that employee's company."""
    company, bypass = _tenant_company()
    if bypass:
        return ""
    if not company:
        return "1=0"
    table = f"`tab{doctype or 'Employee Checkin'}`"
    return f"{table}.`employee` in (select `name` from `tabEmployee` where `company` = {frappe.db.escape(company)})"


def employee_linked_permission(doc, user=None, permission_type=None, ptype=None, **_ignored):
    permission_type = permission_type or ptype  # Frappe passes the right as ptype
    company, bypass = _tenant_company()
    if bypass:
        return True
    if not company:
        return False
    return bool(doc.get("employee")) and frappe.db.get_value("Employee", doc.employee, "company") == company


def read_only_permission(doc, user=None, permission_type=None, ptype=None, **_ignored):
    """HR Settings and Payroll Settings: every tenant reads them, only vendor staff change them."""
    _company, bypass = _tenant_company()
    if bypass:
        return True
    return (permission_type or ptype) not in {"create", "write", "delete", "submit", "cancel", "amend"}


def ensure_holiday_assignment(doc, method=None, *args, **kwargs):
    """``Employee`` after_insert: HRMS wants a Holiday List Assignment for leave and payroll.

    A new employee gets one from their own holiday list, or the company's default, starting on the joining date,
    so leave and salary work from the first day without a separate setup step.
    """
    holiday_list = doc.get("holiday_list") or frappe.db.get_value("Company", doc.get("company"), "default_holiday_list")
    if not holiday_list or not doc.get("date_of_joining"):
        return
    if frappe.db.exists("Holiday List Assignment", {"applicable_for": "Employee", "assigned_to": doc.name, "docstatus": 1}):
        return
    try:
        assignment = frappe.get_doc({
            "doctype": "Holiday List Assignment", "applicable_for": "Employee", "assigned_to": doc.name,
            "holiday_list": holiday_list, "from_date": doc.date_of_joining,
        })
        assignment.insert(ignore_permissions=True)
        assignment.submit()
    except Exception:  # noqa: BLE001  (never block saving an employee over this)
        frappe.log_error(title="Holiday list assignment for a new employee failed")
