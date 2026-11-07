"""CRM team management test on the demo tenants: add, access check, remove."""

import sys
import frappe

frappe.init(site=sys.argv[1])
frappe.connect()
from reckon_crm.api.team import add_member, list_members, remove_member

ADMIN = "demo.crm.alpha@example.com"
MEMBER = "demo.crm.member@example.com"

frappe.set_user(ADMIN)
try:
    add_member(MEMBER, "CRM Demo Member", "Company Manager")
    print("ADDED", MEMBER, [m.user for m in list_members()])
finally:
    frappe.set_user("Administrator")
frappe.db.commit()

print("MEMBER_ROLES", sorted(r for r in frappe.get_roles(MEMBER) if r.startswith("Reckon CRM")))
frappe.set_user(MEMBER)
try:
    print("MEMBER_SEES", sorted({r.company for r in frappe.get_list("CRM Lead", fields=["company"], limit_page_length=0)}))
finally:
    frappe.set_user("Administrator")

frappe.set_user(ADMIN)
try:
    remove_member(MEMBER)
    print("REMOVED", MEMBER)
finally:
    frappe.set_user("Administrator")
frappe.db.commit()
print("AFTER_REMOVE_ROLES", sorted(r for r in frappe.get_roles(MEMBER) if r.startswith("Reckon CRM")))
print("AFTER_REMOVE_PERMS", frappe.get_all("User Permission", filters={"user": MEMBER, "allow": "Company"}, pluck="for_value"))
