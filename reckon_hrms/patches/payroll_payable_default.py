"""Give every company with HRMS employees a default payroll payable account. Idempotent."""

import frappe

from reckon_hrms.payroll import ensure_payroll_payable


def execute():
    companies = frappe.get_all(
        "Company",
        filters={"default_payroll_payable_account": ["is", "not set"]},
        pluck="name",
    )
    with_people = set(frappe.get_all("Employee", pluck="company", distinct=True))
    for company in companies:
        if company in with_people:
            ensure_payroll_payable(company)
