"""Run the CRM tenant seed for the demo companies (the platform runs it per tenant)."""

import sys
import frappe

frappe.init(site=sys.argv[1])
frappe.connect()
from reckon_crm.seed import run_crm_seed

for company in ["RD Demo CRM Alpha Ltd", "RD Demo CRM Beta Ltd"]:
    print("SEEDED", run_crm_seed(company, "demo-1"))
frappe.db.commit()
