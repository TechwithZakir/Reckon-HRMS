"""Create two demo SaaS tenants for Reckon HRMS and check company isolation.

Run on a bench:  bench --site <site> execute reckon_hrms.scripts... (see README)
Idempotent: existing demo records are reused. Demo names carry the RD Demo prefix.
"""

import secrets
import sys
from datetime import date

import frappe

from reckon_saas_platform.saas import (
    _assign_company_admin,
    _create_tenant_admin_user,
    _create_tenant_company,
)

DEMO = [
    ("RD Demo Alpha Ltd", "demo.alpha@example.com", "Alpha Demo Owner"),
    ("RD Demo Beta Ltd", "demo.beta@example.com", "Beta Demo Owner"),
]
HRMS_ROLES = ["Reckon HRMS Admin", "Reckon HRMS Manager", "Reckon HRMS Employee"]
SAMPLE_EMPLOYEES = {
    "RD Demo Alpha Ltd": ["Rahim Uddin", "Karim Hasan"],
    "RD Demo Beta Ltd": ["Nasir Ahmed", "Salma Akter"],
}


def ensure_roles():
    for role in HRMS_ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
                ignore_permissions=True
            )


def ensure_tenant(company_name, email, owner_name):
    if not frappe.db.exists("Company", company_name):
        _create_tenant_company(company_name)
    password = None
    if not frappe.db.exists("User", email):
        password = secrets.token_urlsafe(12)
        _create_tenant_admin_user(email, owner_name, saas_module="hrms", password=password)
    _assign_company_admin(email, company_name)
    return password


def ensure_employees(company_name):
    for i, full_name in enumerate(SAMPLE_EMPLOYEES[company_name], start=1):
        first, _, last = full_name.partition(" ")
        if frappe.db.exists("Employee", {"company": company_name, "employee_name": full_name}):
            continue
        frappe.get_doc(
            {
                "doctype": "Employee",
                "first_name": first,
                "last_name": last,
                "employee_name": full_name,
                "gender": "Male",
                "date_of_birth": date(1995, i, 10),
                "date_of_joining": date(2025, i, 1),
                "status": "Active",
                "company": company_name,
            }
        ).insert(ignore_permissions=True)


def ensure_attendance(company_name):
    today = date.today()
    for emp in frappe.get_all("Employee", {"company": company_name}, pluck="name"):
        if frappe.db.exists("Attendance", {"employee": emp, "attendance_date": today}):
            continue
        frappe.get_doc(
            {
                "doctype": "Attendance",
                "employee": emp,
                "attendance_date": today,
                "status": "Present",
                "company": company_name,
            }
        ).insert(ignore_permissions=True)


def main():
    ensure_roles()
    created = {}
    for company_name, email, owner_name in DEMO:
        password = ensure_tenant(company_name, email, owner_name)
        ensure_employees(company_name)
        ensure_attendance(company_name)
        created[email] = password
    frappe.db.commit()
    for email, password in created.items():
        print("DEMO_PASSWORD", email, password or "(existing user, password unchanged)")
    print("DEMO_DONE", [c for c, _, _ in DEMO])
    return created


if __name__ == "__main__":
    frappe.init(site=sys.argv[1])
    frappe.connect()
    main()
