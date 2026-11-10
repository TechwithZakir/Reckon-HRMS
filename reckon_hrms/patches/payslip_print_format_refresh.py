"""Refresh the Reckon Payslip print format HTML from the code (amount in words fix). Idempotent."""

import frappe

from reckon_hrms.patches.payslip_print_format import HTML, NAME


def execute():
    if frappe.db.exists("Print Format", NAME):
        frappe.db.set_value("Print Format", NAME, "html", HTML)
        frappe.clear_cache(doctype="Salary Slip")
