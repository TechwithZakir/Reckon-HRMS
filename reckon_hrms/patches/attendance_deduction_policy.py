"""Company settings for the late-entry and early-exit deduction policy. Idempotent."""

import frappe

FIELDS = [
    {"fieldname": "reckon_marks_per_day", "fieldtype": "Int", "label": "Late or early marks equal one day",
     "default": "3", "description": "Every this many days with a late entry or early exit deducts one day's pay."},
    {"fieldname": "reckon_deduction_divisor", "fieldtype": "Int", "label": "Daily pay divisor",
     "default": "30", "description": "Base salary divided by this gives one day's pay for the deduction."},
    {"fieldname": "reckon_deduction_cap", "fieldtype": "Currency", "label": "Monthly cap on attendance deduction",
     "default": "0", "description": "Zero means no cap."},
]


def execute():
    for field in FIELDS:
        if frappe.db.exists("Custom Field", {"dt": "Company", "fieldname": field["fieldname"]}):
            continue
        frappe.get_doc({"doctype": "Custom Field", "dt": "Company", "insert_after": "reckon_industry",
                        **field}).insert(ignore_permissions=True)
    frappe.clear_cache(doctype="Company")
