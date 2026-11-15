"""Give every component on an existing salary slip its company account, so earlier payroll runs can book their payment."""

import frappe

from reckon_hrms.component_accounts import ensure_component_accounts


def execute():
    for name in frappe.get_all("Salary Slip", filters={"docstatus": ["<", 2]}, pluck="name"):
        ensure_component_accounts(frappe.get_doc("Salary Slip", name))
