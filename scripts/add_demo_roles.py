"""Add the Reckon HRMS admin role to the demo tenant admins (created before the role existed)."""

import sys
import frappe

DEMO_USERS = ["demo.hrms.alpha@example.com", "demo.hrms.beta@example.com"]
ROLE = "Reckon HRMS Admin"

frappe.init(site=sys.argv[1])
frappe.connect()
for email in DEMO_USERS:
    user = frappe.get_doc("User", email)
    user.add_roles(ROLE)
    print("ROLE_ADDED", email, ROLE in frappe.get_roles(email))
frappe.db.commit()
