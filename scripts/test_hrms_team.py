"""HRMS team management test on the demo tenants: add, check access, remove."""

import sys
import frappe

frappe.init(site=sys.argv[1])
frappe.connect()
from reckon_hrms.api.team import add_member, list_members, remove_member

ADMIN = "demo.hrms.alpha@example.com"
MEMBER = "demo.hrms.member@example.com"
COMPANY = "RD Demo HRMS Alpha Ltd"

frappe.set_user(ADMIN)
try:
    add_member(MEMBER, "HRMS Demo Member", "Company User")
    print("ADDED", MEMBER, [m.user for m in list_members()])
finally:
    frappe.set_user("Administrator")
frappe.db.commit()

roles = frappe.get_roles(MEMBER)
print("MEMBER_ROLES", sorted(r for r in roles if r.startswith("Reckon HRMS")))
frappe.set_user(MEMBER)
try:
    print("MEMBER_SEES", sorted({r.company for r in frappe.get_list("Employee", fields=["company"], limit_page_length=0)}))
finally:
    frappe.set_user("Administrator")

frappe.set_user(ADMIN)
try:
    remove_member(MEMBER)
    print("REMOVED", MEMBER)
finally:
    frappe.set_user("Administrator")
frappe.db.commit()
roles_after = frappe.get_roles(MEMBER)
print("AFTER_REMOVE_ROLES", sorted(r for r in roles_after if r.startswith("Reckon HRMS")))
print("AFTER_REMOVE_PERMS", frappe.get_all("User Permission", filters={"user": MEMBER, "allow": "Company"}, pluck="for_value"))
