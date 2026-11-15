"""Company on Branch and Employment Type, and the Component Type field the payroll reports read.

Standard HRMS reports select ``Salary Component.component_type``, which HRMS only creates for India. Without it
they fail with an unknown column, so it is added here and the provident fund component is tagged.
"""

import frappe

from reckon_hrms.patches.company_on_shared_masters import execute as add_company_fields


def execute():
    add_company_fields()
    if frappe.db.exists("DocType", "Salary Component") and not frappe.db.has_column("Salary Component", "component_type"):
        frappe.get_doc({
            "doctype": "Custom Field", "dt": "Salary Component", "fieldname": "component_type", "label": "Component Type",
            "fieldtype": "Select", "insert_after": "description", "translatable": 0,
            "options": "
Provident Fund
Additional Provident Fund
Provident Fund Loan
Professional Tax",
            "depends_on": 'eval:doc.type == "Deduction"',
        }).insert(ignore_permissions=True)
        frappe.clear_cache(doctype="Salary Component")
    if frappe.db.has_column("Salary Component", "component_type"):
        for name in frappe.get_all("Salary Component", filters={"salary_component": ["like", "Provident Fund%"], "component_type": ["in", ["", None]]}, pluck="name"):
            frappe.db.set_value("Salary Component", name, "component_type", "Provident Fund", update_modified=False)
