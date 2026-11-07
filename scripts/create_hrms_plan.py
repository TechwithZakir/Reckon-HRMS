"""Create the HRMS Standard SaaS plan (same shape as the existing Standard plan)."""

import sys
import frappe

PLAN = {
    "plan_name": "HRMS Standard",
    "saas_module": "hrms",
    "plan_version": 1,
    "currency": "BDT",
    "price": 1000,
    "billing_cycle": "Monthly",
    "trial_days": 15,
    "grace_days": 5,
    "enabled": 1,
}

frappe.init(site=sys.argv[1])
frappe.connect()
if frappe.db.exists("SaaS Plan", PLAN["plan_name"]):
    print("PLAN_EXISTS", PLAN["plan_name"])
else:
    frappe.get_doc({"doctype": "SaaS Plan", **PLAN}).insert(ignore_permissions=True)
    frappe.db.commit()
    print("PLAN_CREATED", PLAN["plan_name"])
