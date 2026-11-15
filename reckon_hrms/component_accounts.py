"""Give each salary component the company accounts a payroll posting needs.

HRMS refuses to submit a slip, or book a payroll run, for a component that has no account for the slip's company.
A tenant's own components and the shared catalog both start without one, so the first slip adds them from the
company's own Salary expense account (earnings) and payroll payable account (deductions).
"""

from __future__ import annotations

import frappe


def _accounts_for(company: str) -> dict[str, str | None]:
    expense = frappe.db.get_value(
        "Account", {"company": company, "is_group": 0, "root_type": "Expense", "account_name": ["like", "Salary%"]}, "name"
    )
    payable = frappe.db.get_value("Company", company, "default_payroll_payable_account")
    return {"Earning": expense, "Deduction": payable}


def ensure_component_accounts(doc, method=None, *args, **kwargs) -> None:
    """``Salary Slip`` before_validate: add the company's account to every component on the slip."""
    company = doc.get("company")
    if not company:
        return
    accounts = None
    for row in list(doc.get("earnings") or []) + list(doc.get("deductions") or []):
        component = row.get("salary_component")
        if not component or frappe.db.exists("Salary Component Account", {"parent": component, "company": company}):
            continue
        accounts = accounts or _accounts_for(company)
        account = accounts.get(frappe.db.get_value("Salary Component", component, "type") or "Earning")
        if not account:
            continue
        frappe.get_doc({
            "doctype": "Salary Component Account", "parent": component, "parenttype": "Salary Component",
            "parentfield": "accounts", "company": company, "account": account,
        }).insert(ignore_permissions=True)
