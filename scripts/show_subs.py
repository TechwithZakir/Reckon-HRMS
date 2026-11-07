import sys
import frappe

frappe.init(site=sys.argv[1])
frappe.connect()
for name in ["SUB-00003", "SUB-00004"]:
    s = frappe.get_doc("SaaS Subscription", name)
    print("SUB", name, s.company, s.saas_module, s.status, s.plan, s.price, s.start_date, s.trial_end_date, s.grace_until)
print("PAYMENTS", frappe.get_all("SaaS Payment", fields=["name", "subscription", "status", "amount"], limit=10))
