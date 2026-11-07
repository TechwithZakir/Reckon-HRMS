import sys
import frappe

frappe.init(site=sys.argv[1])
frappe.connect()
print("WS", frappe.get_all("Workspace", filters=[["name", "like", "%HRMS%"]], pluck="name"))
print("MODULES", frappe.get_all("SaaS Module", fields=["name", "enabled", "landing_workspace", "app_name"]))
print("PLANS", frappe.get_all("SaaS Plan", fields=["name"]))
print("PLAN_META", [f.fieldname for f in frappe.get_meta("SaaS Plan").fields])
print("SUB_META", [f.fieldname for f in frappe.get_meta("SaaS Subscription").fields][:30])
