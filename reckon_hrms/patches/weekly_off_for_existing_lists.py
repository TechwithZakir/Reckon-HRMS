"""Holiday Lists made when a tenant was created had a weekly off day named but no weekly off rows, so every day counted as a working day.

Fills them in for each list that has none, from the list's own day or the usual days of the company's country. Lists that already
have weekly off rows are never touched. Idempotent.
"""

import frappe

from reckon_hrms.seed import fill_weekly_off, weekly_off_days


def execute():
    if not frappe.db.exists("DocType", "Holiday List"):
        return
    for name in frappe.get_all("Holiday List", filters={"company": ["is", "set"]}, pluck="name"):
        if frappe.db.exists("Holiday", {"parent": name, "weekly_off": 1}):
            continue
        doc = frappe.get_doc("Holiday List", name)
        if fill_weekly_off(doc, weekly_off_days(doc.company, doc.weekly_off)):
            doc.flags.ignore_permissions = True
            doc.save()
