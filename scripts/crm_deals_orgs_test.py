"""CRM isolation test for Organizations and Deals, run as each demo tenant user."""

import sys
import frappe

frappe.init(site=sys.argv[1])
frappe.connect()

TENANTS = {"RD Demo CRM Alpha Ltd": "demo.crm.alpha@example.com",
           "RD Demo CRM Beta Ltd": "demo.crm.beta@example.com"}

for company, email in TENANTS.items():
    frappe.set_user(email)
    try:
        org_name = f"{company} Org"
        if not frappe.db.exists("CRM Organization", {"organization_name": org_name}):
            frappe.get_doc({"doctype": "CRM Organization", "organization_name": org_name}).insert()
        if not frappe.db.exists("CRM Deal", {"organization": org_name, "company": company}):
            frappe.get_doc({"doctype": "CRM Deal", "organization": org_name}).insert()
    except Exception as exc:
        print("CREATE_ERR", company, type(exc).__name__, str(exc)[:160])
    finally:
        frappe.set_user("Administrator")
frappe.db.commit()

alpha, beta = TENANTS["RD Demo CRM Alpha Ltd"], TENANTS["RD Demo CRM Beta Ltd"]
for doctype in ("CRM Organization", "CRM Deal"):
    for company, email in TENANTS.items():
        frappe.set_user(email)
        try:
            rows = frappe.get_list(doctype, fields=["name", "company"], limit_page_length=0)
            companies = sorted({r.company for r in rows})
        finally:
            frappe.set_user("Administrator")
        print("VISIBLE", doctype, email, companies, len(rows), "OK" if companies in ([company], []) else "LEAK")
    beta_doc = frappe.db.get_value(doctype, {"company": "RD Demo CRM Beta Ltd"}, "name")
    frappe.set_user(alpha)
    try:
        frappe.get_doc(doctype, beta_doc).check_permission("read")
        print("CROSS_READ", doctype, "ALLOWED (BAD)")
    except frappe.PermissionError:
        print("CROSS_READ", doctype, "denied (OK)")
    finally:
        frappe.set_user("Administrator")
