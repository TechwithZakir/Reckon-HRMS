"""Reckon HRMS menu: one definition for the desk left nav, the cards and the web pages.

Items: ("DocType", name) | ("Report", name) | ("URL", path, label). Icons are Lucide names.
"""

# Each item appears once, so the left nav and the cards stay in step.
MENU = (
    ("Featured", (
        ("Page", "reckon-hrms-home", "My home"),
        ("Page", "reckon-hrms-checkin", "Check in / out"),
        ("DocType", "Leave Application"),
        ("DocType", "Expense Claim"),
        ("DocType", "Payroll Entry"),
        ("DocType", "Employee"),
    )),
    ("Dashboards & Reports", (
        ("Page", "reckon-hrms-home", "Dashboard"),
        ("Report", "Monthly Attendance Sheet"),
        ("Report", "Employee Leave Balance"),
        ("Report", "Salary Register"),
    )),
    ("People", (
        ("DocType", "Department"),
        ("DocType", "Designation"),
        ("DocType", "HRMS Office Location"),
    )),
    ("Time & Attendance", (
        ("DocType", "Attendance"),
        ("DocType", "Employee Checkin"),
        ("DocType", "Shift Type"),
        ("DocType", "Shift Assignment"),
        ("DocType", "Holiday List"),
        ("DocType", "Holiday List Assignment"),
    )),
    ("Leave & Expenses", (
        ("DocType", "Leave Type"),
        ("DocType", "Leave Allocation"),
        ("DocType", "Expense Claim Type"),
    )),
    ("Payroll", (
        ("DocType", "Salary Slip"),
        ("DocType", "Salary Structure"),
        ("DocType", "Salary Structure Assignment"),
        ("DocType", "Salary Component"),
        ("DocType", "Additional Salary"),
    )),
)

# Lucide icon names for each left-nav item, keyed by its label.
ICONS = {
    "My home": "layout-dashboard",
    "Check in / out": "log-in",
    "Leave Application": "calendar-days",
    "Expense Claim": "receipt",
    "Payroll Entry": "wallet",
    "Employee": "users",
    "Dashboard": "gauge",
    "Monthly Attendance Sheet": "file-spreadsheet",
    "Employee Leave Balance": "calendar-check",
    "Salary Register": "banknote",
    "Department": "building-2",
    "Designation": "id-card",
    "HRMS Office Location": "map-pin",
    "Attendance": "user-check",
    "Employee Checkin": "fingerprint",
    "Shift Type": "clock",
    "Shift Assignment": "timer",
    "Holiday List": "calendar-off",
    "Holiday List Assignment": "calendar-range",
    "Leave Type": "tag",
    "Leave Allocation": "plus-circle",
    "Expense Claim Type": "list",
    "Salary Slip": "file-text",
    "Salary Structure": "layers",
    "Salary Structure Assignment": "link",
    "Salary Component": "puzzle",
    "Additional Salary": "plus",
}
