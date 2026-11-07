"""Desk guard check for the demo tenants: allowed and blocked Desk and API paths."""

import sys
import frappe

frappe.init(site=sys.argv[1])
frappe.connect()
from reckon_saas_platform.desk_module_guard import enforce_module_desk_access, guarded_module_for_user


class _Req:
    def __init__(self, path):
        self.path = path
        self.method = "GET"


CASES = {
    "demo.hrms.alpha@example.com": [
        ("/app/employee/EMP-0001", True), ("/app/leave-application", True),
        ("/app/reckon-hrms", True), ("/app/sales-invoice", False),
        ("/api/resource/Employee", True), ("/api/resource/Sales%20Invoice", False),
    ],
    "demo.crm.alpha@example.com": [
        ("/app/crm-lead", True), ("/app/crm-deal", True), ("/app/employee", False),
        ("/api/resource/CRM%20Lead", True), ("/api/resource/Employee", False),
    ],
}
for email, checks in CASES.items():
    module = guarded_module_for_user(email)
    print("MODULE", email, module.get("key") if module else None)
    for path, expect in checks:
        frappe.set_user(email)
        frappe.local.request = _Req(path)
        try:
            enforce_module_desk_access()
            got = True
        except frappe.PermissionError:
            got = False
        finally:
            frappe.set_user("Administrator")
        print("CHECK", path, "allowed" if got else "blocked", "OK" if got == expect else "UNEXPECTED")
