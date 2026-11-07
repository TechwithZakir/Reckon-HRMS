"""Module role test: a Payroll Manager and an Employee Self Service member of the alpha company.

Adds each member as the company admin, checks the Frappe roles they get and what they can read
(their own company only), then removes them and deletes their test logins.
"""

import sys
import frappe

frappe.init(site=sys.argv[1])
frappe.connect()
from reckon_saas_platform.team import add_team_member, remove_team_member

ADMIN = "demo.hrms.alpha@example.com"
COMPANY = "RD Demo HRMS Alpha Ltd"
MEMBERS = {
    "demo.payroll.member@example.com": "Payroll Manager",
    "demo.ess.member@example.com": "Employee Self Service",
}

ess_email = "demo.ess.member@example.com"
if not frappe.db.exists("User", ess_email):
    frappe.get_doc({"doctype": "User", "email": ess_email, "first_name": "ESS Demo", "enabled": 1,
                    "send_welcome_email": 0}).insert(ignore_permissions=True)
if not frappe.db.exists("Employee", {"user_id": ess_email}):
    frappe.get_doc({"doctype": "Employee", "first_name": "ESS", "last_name": "Demo", "gender": "Male",
                    "date_of_birth": "1996-03-01", "date_of_joining": "2025-02-01", "status": "Active",
                    "company": "RD Demo HRMS Alpha Ltd", "user_id": ess_email}).insert(ignore_permissions=True)
frappe.db.commit()

frappe.set_user(ADMIN)
try:
    for email, role in MEMBERS.items():
        add_team_member(email, email.split("@")[0], "Company Manager", role)
finally:
    frappe.set_user("Administrator")
frappe.db.commit()

beta_employee = frappe.db.get_value("Employee", {"company": "RD Demo HRMS Beta Ltd"}, "name")
for email, role in MEMBERS.items():
    roles = sorted(r for r in frappe.get_roles(email) if r in (
        "HR Manager", "Payroll Manager", "Interviewer", "Employee Self Service") or r.startswith("Reckon HRMS"))
    print("ROLES", email, roles)
    print("DB_ROLES", email, sorted(frappe.get_all("Has Role", {"parent": email, "parenttype": "User"}, pluck="role")))
    frappe.set_user(email)
    try:
        companies = sorted({r.company for r in frappe.get_list("Employee", fields=["company"], limit_page_length=0)})
        print("EMPLOYEE_SEES", email, companies)
        try:
            frappe.get_doc("Employee", beta_employee).check_permission("read")
            print("CROSS_READ", email, "ALLOWED (BAD)")
        except frappe.PermissionError:
            print("CROSS_READ", email, "denied (OK)")
    finally:
        frappe.set_user("Administrator")

frappe.set_user(ADMIN)
try:
    for email in MEMBERS:
        remove_team_member(email)
finally:
    frappe.set_user("Administrator")
frappe.db.commit()
for email in MEMBERS:
    for name in frappe.get_all("Tenant User Assignment", {"user": email}, pluck="name"):
        frappe.delete_doc("Tenant User Assignment", name, ignore_permissions=True, force=True)
    frappe.delete_doc("User", email, ignore_permissions=True, force=True)
for name in frappe.get_all("Employee", {"user_id": email}, pluck="name"):
        frappe.delete_doc("Employee", name, ignore_permissions=True, force=True)
frappe.db.commit()
print("CLEANED", len(MEMBERS))
