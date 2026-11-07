"""Create the shared Payroll Manager role: payroll documents only. Company scoping comes from the platform."""

import frappe

ROLE = "Payroll Manager"
PAYROLL_GRANTS = {
    "Salary Structure": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
    "Salary Structure Assignment": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
    "Payroll Entry": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
    "Salary Slip": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
    "Employee": {"read": 1},
    "Attendance": {"read": 1},
}


def execute():
    if not frappe.db.exists("Role", ROLE):
        frappe.get_doc({"doctype": "Role", "role_name": ROLE, "desk_access": 1}).insert(ignore_permissions=True)
    for doctype, flags in PAYROLL_GRANTS.items():
        if not frappe.db.exists("DocType", doctype):
            continue
        if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": ROLE, "permlevel": 0}):
            continue
        frappe.get_doc({
            "doctype": "Custom DocPerm", "parent": doctype, "parenttype": "DocType",
            "parentfield": "permissions", "role": ROLE, "permlevel": 0,
            **{k: flags.get(k, 0) for k in ("read", "write", "create", "delete", "submit", "cancel")},
        }).insert(ignore_permissions=True)
    frappe.clear_cache()
