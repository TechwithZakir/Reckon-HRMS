"""Add a Company field to Holiday List, and group the Reckon HRMS workspace into its four modules.

Holiday List has no Company field in Frappe HRMS, so a default calendar would be shared by all
tenants. This adds a Company link (a Custom Field) so each tenant's calendar is its own.
The workspace links group the Desk sidebar by module. Idempotent.
"""

import frappe

from reckon_hrms.constants import MODULE_FEATURES  # noqa: F401  (documents the four modules)

WORKSPACE_GROUPS = (
    ("Employees", ("Employee", "Department", "Designation")),
    ("Attendance & Shifts", ("Attendance", "Shift Type", "Shift Assignment", "Holiday List")),
    ("Leave", ("Leave Application", "Leave Type")),
    ("Payroll", ("Salary Structure", "Salary Structure Assignment", "Payroll Entry", "Salary Slip",
                 "Salary Component")),
)
WORKSPACE = "Reckon HRMS"


def _ensure_holiday_list_company():
    name = "Holiday List-company"
    if not frappe.db.exists("Custom Field", name):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Holiday List",
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company",
        }).insert(ignore_permissions=True)


def _group_workspace_links():
    if not frappe.db.exists("Workspace", WORKSPACE):
        return
    ws = frappe.get_doc("Workspace", WORKSPACE)
    wanted = []
    for group, doctypes in WORKSPACE_GROUPS:
        wanted.append({"type": "Card Break", "label": group})
        for doctype in doctypes:
            if frappe.db.exists("DocType", doctype):
                wanted.append({"type": "Link", "link_type": "DocType", "link_to": doctype, "label": doctype})
    current = [(row.type, row.label, row.link_to) for row in ws.links]
    target = [(row["type"], row["label"], row.get("link_to")) for row in wanted]
    if current == target:
        return
    ws.set("links", [])
    for row in wanted:
        ws.append("links", row)
    ws.save(ignore_permissions=True)


def execute():
    _ensure_holiday_list_company()
    _group_workspace_links()
    frappe.clear_cache()
