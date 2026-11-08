"""Add the payment-hold fields to Salary Slip (Page 3, step 5). Idempotent."""

import frappe

FIELDS = [
    {"fieldname": "reckon_payment_hold", "fieldtype": "Check", "label": "Hold payment"},
    {"fieldname": "reckon_hold_reason", "fieldtype": "Small Text", "label": "Hold reason",
     "depends_on": "eval:doc.reckon_payment_hold"},
    # Bank payment journal. Separate from HRMS's own journal_entry, which holds the accrual entry.
    {"fieldname": "reckon_payment_entry", "fieldtype": "Link", "options": "Journal Entry",
     "label": "Payment journal entry", "read_only": 1},
]


def execute():
    for field in FIELDS:
        if frappe.db.exists("Custom Field", {"dt": "Salary Slip", "fieldname": field["fieldname"]}):
            continue
        frappe.get_doc({"doctype": "Custom Field", "dt": "Salary Slip", "insert_after": "payroll_entry",
                        **field}).insert(ignore_permissions=True)
    frappe.clear_cache(doctype="Salary Slip")
