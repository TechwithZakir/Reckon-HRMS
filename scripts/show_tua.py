import sys
import frappe

frappe.init(site=sys.argv[1])
frappe.connect()
for u in ["demo.hrms.alpha@example.com", "demo.hrms.beta@example.com"]:
    rows = frappe.get_all("Tenant User Assignment", filters={"user": u}, fields=["name", "company", "active", "is_default", "valid_from", "valid_to", "role_profile"])
    print("TUA", u, rows)
    print("GET_USER_COMPANIES", u, frappe.get_attr("reckon_saas_platform.tenant_security.get_user_companies")(u))
