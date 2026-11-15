"""Add a Company field to the shared reference masters so a tenant's own rows can be kept apart.

The vendor's seeded rows keep an empty Company and stay a read-only catalog for every tenant.
"""

import frappe

from reckon_hrms.constants import SHARED_CATALOG_DOCTYPES


def execute():
    for doctype in SHARED_CATALOG_DOCTYPES:
        if not frappe.db.exists("DocType", doctype) or frappe.db.has_column(doctype, "company"):
            continue
        name = f"{doctype}-company"
        if frappe.db.exists("Custom Field", name):
            continue
        frappe.get_doc({
            "doctype": "Custom Field", "dt": doctype, "fieldname": "company", "label": "Company", "fieldtype": "Link",
            "options": "Company", "no_copy": 1,
            "description": "Empty for the shared catalog; set for a company's own entry.",
        }).insert(ignore_permissions=True)
    frappe.clear_cache()
