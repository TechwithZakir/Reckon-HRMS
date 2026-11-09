"""Starter masters for the industry segment a tenant admin chooses at onboarding.

Applied on request, never silently at provisioning. Every step is get-or-create, so a repeat is
safe. Deliberately not created here:
- salary structures and amounts (the admin reviews the component list and sets amounts);
- leave entitlement days (the guide says leave rules are company-configured);
- anything for another tenant.
"""

from __future__ import annotations

import frappe

from reckon_hrms import salary_suggest

# Component names are shared with the existing starter set so they are reused, not duplicated.
COMPONENT_ABBR = {
    "Basic Salary": "BASIC",
    "House Rent Allowance": "HRA",
    "Medical Allowance": "MED",
    "Conveyance Allowance": "CONV",
    "Mobile Allowance": "MOB",
    "Meal Allowance": "MEAL",
    "Attendance Incentive": "ATTINC",
    "Performance Bonus": "PERF",
    "Festival Bonus": "FESTIVAL",
    "Overtime": "OT",
    "Shift Allowance": "SHIFT",
    "Site Allowance": "SITE",
    "Sales Commission": "COMM",
    "Loan Recovery": "LOANREC",
    "Salary Advance Recovery": "ADVREC",
    "Other Adjustment": "ADJ",
}
DEDUCTION_COMPONENTS = {"Loan Recovery", "Salary Advance Recovery", "Other Adjustment"}
LWP_LEAVE_TYPES = {"Unpaid Leave"}


def _component(name: str) -> str:
    """Create one component master if missing. Returns 'created', 'exists' or 'skipped'."""
    if frappe.db.exists("Salary Component", name):
        return "exists"
    abbr = COMPONENT_ABBR[name]
    if frappe.db.exists("Salary Component", {"salary_component_abbr": abbr}):
        return "skipped"
    frappe.get_doc({
        "doctype": "Salary Component",
        "salary_component": name,
        "salary_component_abbr": abbr,
        "type": "Deduction" if name in DEDUCTION_COMPONENTS else "Earning",
    }).insert(ignore_permissions=True)
    return "created"


def _leave_type(name: str) -> str:
    if frappe.db.exists("Leave Type", name):
        return "exists"
    doc = {"doctype": "Leave Type", "leave_type_name": name, "max_leaves_allowed": 0}
    if name in LWP_LEAVE_TYPES:
        doc["is_lwp"] = 1
    frappe.get_doc(doc).insert(ignore_permissions=True)
    return "created"


OVERTIME_TYPE = "Standard Overtime"


def _overtime_type() -> str:
    """Shared overtime rule used by HRMS overtime slips. Created once; the multiplier is a starting point."""
    if frappe.db.exists("Overtime Type", OVERTIME_TYPE):
        return "exists"
    frappe.get_doc({
        "doctype": "Overtime Type", "name": OVERTIME_TYPE,
        "overtime_salary_component": "Overtime",
        "applicable_salary_component": [{"salary_component": "Basic Salary"}],
        "standard_multiplier": 2.0,
        "applicable_for_weekend": 0, "applicable_for_public_holiday": 0,
    }).insert(ignore_permissions=True)
    return "created"


def _component_account(company: str, name: str) -> str | None:
    """The company account a pay item posts to: payroll payable for deductions, a salary expense for earnings."""
    if name in DEDUCTION_COMPONENTS:
        return frappe.db.get_value("Company", company, "default_payroll_payable_account")
    return frappe.db.get_value("Account", {"company": company, "is_group": 0, "root_type": "Expense",
                                           "account_name": ["like", "%Salar%"]}, "name")


def _ensure_component_account(company: str, name: str) -> str:
    """Add the company's account row to a component master if missing. Returns 'set', 'exists' or 'missing'."""
    component = frappe.get_doc("Salary Component", name)
    if any(row.company == company for row in component.accounts):
        return "exists"
    account = _component_account(company, name)
    if not account:
        return "missing"
    component.append("accounts", {"company": company, "account": account})
    component.save(ignore_permissions=True)
    return "set"


def _designation(name: str) -> str:
    if frappe.db.exists("Designation", name):
        return "exists"
    frappe.get_doc({"doctype": "Designation", "designation_name": name}).insert(ignore_permissions=True)
    return "created"


def _department(company: str, name: str) -> str:
    if frappe.db.exists("Department", {"department_name": name, "company": company}):
        return "exists"
    frappe.get_doc({"doctype": "Department", "department_name": name, "company": company}).insert(
        ignore_permissions=True)
    return "created"


def apply_segment(company: str, segment: str, data: dict | None = None) -> dict:
    """Seed the company's starter masters for one segment and record the choice on the Company."""
    data = data or salary_suggest.load_benchmark()
    seg = data["segments"].get(segment)
    if not seg:
        frappe.throw(frappe._("Unknown industry: {0}").format(segment))

    counts = {"designations": 0, "departments": 0, "components": 0, "leave_types": 0}
    skipped: list[str] = []

    for role in seg["roles"]:
        counts["designations"] += _designation(role["role"]) == "created"
    for name in seg["departments"]:
        counts["departments"] += _department(company, name) == "created"
    for name in seg["components"] + seg["recovery_deductions"]:
        outcome = _component(name)
        if outcome == "created":
            counts["components"] += 1
        elif outcome == "skipped":
            skipped.append(name)
    for name in seg["leave_types"]:
        counts["leave_types"] += _leave_type(name) == "created"
    overtime = "exists"
    if "Overtime" in seg["components"]:
        overtime = _overtime_type()
        counts["overtime_types"] = int(overtime == "created")

    # Each pay item needs an account for this company, or payroll approval refuses the run.
    accounts = {"set": 0, "exists": 0, "missing": []}
    for name in seg["components"] + seg["recovery_deductions"]:
        if not frappe.db.exists("Salary Component", name):
            continue
        outcome = _ensure_component_account(company, name)
        if outcome == "missing":
            accounts["missing"].append(name)
        else:
            accounts[outcome] += 1

    frappe.db.set_value("Company", company, "reckon_industry", segment)
    return {"company": company, "segment": segment, "label": seg["label"], "created": counts,
            "skipped_components": skipped, "overtime_type": overtime, "component_accounts": accounts}
