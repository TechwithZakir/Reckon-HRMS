import sys
import frappe

frappe.init(site=sys.argv[1])
frappe.connect()
email, company = "demo.hrms.alpha@example.com", "RD Demo HRMS Alpha Ltd"
frappe.set_user(email)
from reckon_saas_platform.tenant_security import get_user_companies, resolve_tenant
print("SESSION", frappe.session.user, "COMPANIES", get_user_companies(email), get_user_companies())
try:
    print("RESOLVE", resolve_tenant(company=company).company)
except Exception as exc:
    print("RESOLVE_ERR", type(exc).__name__, exc)
try:
    frappe.get_doc({"doctype": "Employee", "first_name": "Probe", "last_name": "One", "gender": "Male",
                    "date_of_birth": "1995-01-10", "date_of_joining": "2025-01-01", "status": "Active",
                    "company": company}).insert()
    print("INSERT_OK")
    frappe.db.rollback()
except Exception as exc:
    import traceback; print("INSERT_ERR", type(exc).__name__, str(exc)[:200]); print("FRAMES", [l.strip()[:150] for l in traceback.format_exc().splitlines() if "File \"" in l and "site-packages" not in l][-8:])
    frappe.db.rollback()
