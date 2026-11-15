"""Give every active employee without a Holiday List Assignment one, from their own or the company's holiday list."""

import frappe

from reckon_hrms.tenancy_hooks import ensure_holiday_assignment


def execute():
    for name in frappe.get_all("Employee", filters={"status": "Active"}, pluck="name"):
        ensure_holiday_assignment(frappe.get_doc("Employee", name))
