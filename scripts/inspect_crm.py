import sys
import frappe

frappe.init(site=sys.argv[1])
frappe.connect()
for dt in ["CRM Lead", "CRM Deal", "CRM Organization", "CRM Contact", "CRM Task", "CRM Note", "CRM Call Log"]:
    if not frappe.db.exists("DocType", dt):
        print("MISSING", dt)
        continue
    m = frappe.get_meta(dt)
    print("META", dt, "company" if m.has_field("company") else "NO_COMPANY", "rows", frappe.db.count(dt))
print("CRM_ROLES", frappe.get_all("Role", filters={"name": ["like", "%CRM%"]}, pluck="name"))
print("CRM_SALES", frappe.get_all("Role", filters={"name": ["like", "Sales%"]}, pluck="name"))
