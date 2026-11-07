"""Reset the demo tenant owner passwords and print them once (demo accounts only)."""

import secrets
import sys
import frappe

DEMO_USERS = ["demo.hrms.alpha@example.com", "demo.hrms.beta@example.com",
              "demo.crm.alpha@example.com", "demo.crm.beta@example.com"]

frappe.init(site=sys.argv[1])
frappe.connect()
for email in DEMO_USERS:
    pwd = secrets.token_urlsafe(12)
    from frappe.utils.password import update_password
    update_password(email, pwd)
    print("RESET", email, pwd)
frappe.db.commit()
