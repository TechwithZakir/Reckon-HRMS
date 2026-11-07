"""Company isolation test for the HRMS demo tenants (runs server-side as each tenant user)."""

import sys
from datetime import date

import frappe
from reckon_saas_platform.saas import is_subscription_active

TENANTS = {
    "RD Demo HRMS Alpha Ltd": "demo.hrms.alpha@example.com",
    "RD Demo HRMS Beta Ltd": "demo.hrms.beta@example.com",
}
NAMES = {
    "RD Demo HRMS Alpha Ltd": ["Rahim Uddin", "Karim Hasan"],
    "RD Demo HRMS Beta Ltd": ["Nasir Ahmed", "Salma Akter"],
}


def create_employees(company, email):
    frappe.set_user(email)
    try:
        for i, full in enumerate(NAMES[company], start=1):
            if frappe.db.exists("Employee", {"company": company, "employee_name": full}):
                continue
            first, _, last = full.partition(" ")
            frappe.get_doc({
                "doctype": "Employee", "first_name": first, "last_name": last,
                "employee_name": full, "gender": "Male",
                "date_of_birth": date(1995, i, 10), "date_of_joining": date(2025, i, 1),
                "status": "Active", "company": company,
            }).insert()
    finally:
        frappe.set_user("Administrator")
    frappe.db.commit()


def visible_companies(email, doctype="Employee"):
    frappe.set_user(email)
    try:
        rows = frappe.get_list(doctype, fields=["name", "company"], limit_page_length=0)
        return sorted({r.company for r in rows}), len(rows)
    finally:
        frappe.set_user("Administrator")


def main():
    for company, email in TENANTS.items():
        create_employees(company, email)
    alpha_email, beta_email = TENANTS["RD Demo HRMS Alpha Ltd"], TENANTS["RD Demo HRMS Beta Ltd"]
    for company, email in TENANTS.items():
        companies, count = visible_companies(email)
        print("VISIBLE", email, companies, count)
        print("SUBSCRIBED", company, is_subscription_active(company, "hrms"))
    # Cross-company direct access must be refused.
    alpha_emp = frappe.db.get_value("Employee", {"company": "RD Demo HRMS Alpha Ltd"}, "name")
    beta_emp = frappe.db.get_value("Employee", {"company": "RD Demo HRMS Beta Ltd"}, "name")
    frappe.set_user(alpha_email)
    try:
        frappe.get_doc("Employee", beta_emp).check_permission("read")
        print("CROSS_READ", "ALLOWED (BAD)")
    except frappe.PermissionError:
        print("CROSS_READ", "denied (OK)")
    finally:
        frappe.set_user("Administrator")
    print("OWN_READ", alpha_emp is not None)


if __name__ == "__main__":
    frappe.init(site=sys.argv[1])
    frappe.connect()
    main()
