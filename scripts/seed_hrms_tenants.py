"""Run the HRMS tenant seed for the demo companies (the platform runs it per tenant)."""

import sys
import frappe

frappe.init(site=sys.argv[1])
frappe.connect()
from reckon_hrms.seed import run_hrms_seed

for company in ["RD Demo HRMS Alpha Ltd", "RD Demo HRMS Beta Ltd"]:
    print("SEEDED", run_hrms_seed(company, "demo-1"))
frappe.db.commit()
