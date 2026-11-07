"""Create the Reckon HRMS Desk workspace (the SaaS module's landing page)."""

import frappe

WORKSPACE = "reckon-hrms"
SHORTCUTS = [
    ("Employee", "Employees"),
    ("Attendance", "Attendance"),
    ("Leave Application", "Leave Applications"),
    ("Salary Structure", "Salary Structures"),
    ("Payroll Entry", "Payroll Entry"),
    ("Salary Slip", "Salary Slips"),
]


def execute():
    if frappe.db.exists("Workspace", WORKSPACE):
        return
    doc = frappe.get_doc(
        {
            "doctype": "Workspace",
            "name": WORKSPACE,
            "title": "Reckon HRMS",
            "label": "Reckon HRMS",
            "module": "Reckon HRMS",
            "public": 1,
            "is_hidden": 0,
            "shortcuts": [
                {"type": "DocType", "link_to": doctype, "label": label, "color": "Blue"}
                for doctype, label in SHORTCUTS
            ],
        }
    )
    doc.insert(ignore_permissions=True)
