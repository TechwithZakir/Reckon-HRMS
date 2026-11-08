"""Add the industry segment field to Company, set by the onboarding choice. Idempotent."""

import frappe


def execute():
    if frappe.db.exists("Custom Field", {"dt": "Company", "fieldname": "reckon_industry"}):
        return
    frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Company",
        "fieldname": "reckon_industry",
        "fieldtype": "Data",
        "label": "Industry segment",
        "insert_after": "company_name",
        "read_only": 1,
        "description": "Chosen at onboarding. Sets which starter masters were seeded.",
    }).insert(ignore_permissions=True)
    frappe.clear_cache(doctype="Company")
