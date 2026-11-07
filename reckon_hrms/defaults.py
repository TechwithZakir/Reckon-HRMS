"""Starter masters for a small Bangladeshi business (SME) on Reckon HRMS.

Pure data, no Frappe import, so the rules are unit-testable. These are starting points
the HR owner should review; they are not legal advice.

Company-owned starter data: departments (Department has a Company field).
Shared starter data: shift, leave types, salary components, designations. Those
DocTypes have no Company field, so they are generic and created once for all tenants.
"""

from __future__ import annotations

# Department has a Company field, so each tenant gets its own copy.
DEPARTMENTS = (
    "Management",
    "Human Resources",
    "Accounts and Finance",
    "Sales and Distribution",
    "Operations and Store",
)

# 09:00-17:00 general shift, Friday weekly off is handled through the Holiday List the HR owner sets.
SHIFT_TYPES = (
    {"name": "General Shift", "start_time": "09:00:00", "end_time": "17:00:00"},
)

# Leave entitlements in days per year, following the Bangladesh Labour Act 2006 minimums
# for casual, sick and festival leave. Earned leave accrues from service and is set by HR.
LEAVE_TYPES = (
    {"name": "Casual Leave", "max_leaves_allowed": 10},
    {"name": "Sick Leave", "max_leaves_allowed": 14},
    {"name": "Festival Leave", "max_leaves_allowed": 11},
    {"name": "Earned Leave", "max_leaves_allowed": 0},
)

# Common payslip components. Amounts and percentages are set per employee or structure.
SALARY_COMPONENTS = (
    {"name": "Basic Salary", "abbr": "BASIC", "type": "Earning"},
    {"name": "House Rent Allowance", "abbr": "HRA", "type": "Earning"},
    {"name": "Medical Allowance", "abbr": "MED", "type": "Earning"},
    {"name": "Conveyance Allowance", "abbr": "CONV", "type": "Earning"},
    {"name": "Provident Fund (Employee)", "abbr": "PFEMP", "type": "Deduction"},
    {"name": "Income Tax (TDS)", "abbr": "TDS", "type": "Deduction"},
)

DESIGNATIONS = (
    "Manager",
    "Executive",
    "Officer",
    "Assistant",
    "Accountant",
    "Sales Representative",
    "Store Keeper",
    "Driver",
    "Office Assistant",
)
