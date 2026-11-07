"""Give the Reckon HRMS roles document permissions on the company-owned HRMS doctypes.

Company isolation is enforced by the platform's tenant rules. These rows only let
the module's roles use the doctypes at all. Admin gets full access, manager gets
read/write/create. Employees get no default access here.
"""

import frappe

from reckon_hrms.constants import ADMIN_ROLE, ROLES, TENANT_OWNED_DOCTYPES

MANAGER_ROLE = "Reckon HRMS Manager"

GRANTS = {
    ADMIN_ROLE: {"read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1},
    MANAGER_ROLE: {"read": 1, "write": 1, "create": 1},
}


def execute():
    for role in ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
                ignore_permissions=True
            )
    for doctype in TENANT_OWNED_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            continue
        for role, flags in GRANTS.items():
            if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
                continue
            frappe.get_doc(
                {
                    "doctype": "Custom DocPerm",
                    "parent": doctype,
                    "parenttype": "DocType",
                    "parentfield": "permissions",
                    "role": role,
                    "permlevel": 0,
                    **{k: flags.get(k, 0) for k in ("read", "write", "create", "delete", "submit", "cancel")},
                }
            ).insert(ignore_permissions=True)
    frappe.clear_cache()
