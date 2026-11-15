"""A company's payroll payable account must be of type Payable, or a payroll run cannot be saved."""

import frappe

from reckon_hrms.payroll import ensure_payroll_payable


def execute():
    for company in frappe.get_all("Company", pluck="name"):
        if frappe.db.get_value("Company", company, "default_payroll_payable_account"):
            ensure_payroll_payable(company)
