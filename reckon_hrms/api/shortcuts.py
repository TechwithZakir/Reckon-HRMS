"""Route map: DocType -> /app path. The one place to change when a desk route changes.

Pure Python (no Frappe import) so the mapping stays unit-testable.
"""

from __future__ import annotations

# Desk slug overrides. Anything not listed uses the DocType name, lower-cased with hyphens.
SLUGS = {
    "Branch": "branch",
    "Department": "department",
    "Designation": "designation",
    "Employee Grade": "employee-grade",
    "Employment Type": "employment-type",
    "Employee": "employee",
    "Data Import": "data-import",
    "Holiday List": "holiday-list",
    "Leave Type": "leave-type",
    "Leave Policy": "leave-policy",
    "Leave Policy Assignment": "leave-policy-assignment",
    "Shift Type": "shift-type",
    "Employee Checkin": "employee-checkin",
    "Payroll Period": "payroll-period",
    "Income Tax Slab": "income-tax-slab",
    "Salary Component": "salary-component",
    "Salary Structure": "salary-structure",
    "Salary Structure Assignment": "salary-structure-assignment",
    "Payroll Entry": "payroll-entry",
    "Salary Slip": "salary-slip",
    "Journal Entry": "journal-entry",
    "Company": "company",
    "Fiscal Year": "fiscal-year",
}

ACTIONS = ("list", "new", "form")


def slug(doctype: str) -> str:
    return SLUGS.get(doctype) or doctype.lower().replace(" ", "-")


def route(doctype: str, action: str = "list", name: str | None = None) -> str:
    """The desk path for a DocType: list, new, or one record's form."""
    if action not in ACTIONS:
        raise ValueError(f"unknown action: {action}")
    base = f"/app/{slug(doctype)}"
    if action == "new":
        return f"{base}/new"
    if action == "form":
        if not name:
            raise ValueError("form needs a record name")
        return f"{base}/{name}"
    return base
