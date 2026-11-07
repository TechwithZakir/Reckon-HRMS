import sys
import frappe

frappe.init(site=sys.argv[1])
frappe.connect()
for name in frappe.get_all("SaaS Plan", pluck="name"):
    doc = frappe.get_doc("SaaS Plan", name)
    print("PLAN", name, doc.saas_module, doc.plan_version, doc.currency, doc.price, doc.billing_cycle, doc.trial_days, doc.grace_days, doc.enabled)
    print("FEATURES", name, repr((doc.features or "")[:300]))
