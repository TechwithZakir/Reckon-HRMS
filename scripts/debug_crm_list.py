import sys
import frappe

frappe.init(site=sys.argv[1])
frappe.connect()
email = "demo.crm.alpha@example.com"
print("ROLES", email, sorted(frappe.get_roles(email)))
print("LEADS_DB", frappe.db.get_all("CRM Lead", filters={"company": "RD Demo CRM Alpha Ltd"}, fields=["name", "company"]))
frappe.set_user(email)
print("PERM_READ", frappe.has_permission("CRM Lead", "read", user=email))
print("QUERY", frappe.get_list("CRM Lead", fields=["name", "company"], limit_page_length=0))
print("QCOND", frappe.get_attr("reckon_saas_platform.tenant_security.get_tenant_owned_query")(user=email, doctype="CRM Lead"))
