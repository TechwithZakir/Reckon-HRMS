"""Reckon HRMS menu: one definition for the desk left nav, the cards and the web pages.

Items: ("DocType", name) | ("Report", name) | ("Page", page_name, label). Icons are Lucide names.
Reports or DocTypes that do not exist on a site are skipped when the menu is built.
"""

# Each item appears once, so the left nav and the cards stay in step.
MENU = (
    ("Dashboard", (
        ("Page", "reckon-hrms-home", "Dashboard"),
    )),
    ("People", (
        ("DocType", "Employee"),
        ("DocType", "Department"),
        ("DocType", "Designation"),
        ("DocType", "HRMS Office Location"),
    )),
    ("Time & Attendance", (
        ("Page", "reckon-hrms-checkin", "Check in / out"),
        ("DocType", "Attendance"),
        ("DocType", "Employee Checkin"),
        ("DocType", "Shift Type"),
        ("DocType", "Shift Assignment"),
        ("DocType", "Holiday List"),
        ("DocType", "Holiday List Assignment"),
    )),
    ("Leave & Expense", (
        ("DocType", "Leave Application"),
        ("DocType", "Leave Type"),
        ("DocType", "Leave Allocation"),
        ("DocType", "Expense Claim"),
        ("DocType", "Expense Claim Type"),
    )),
    ("Payroll", (
        ("Page", "reckon-hrms-payout", "Monthly payroll payout"),
        ("DocType", "Payroll Entry"),
        ("DocType", "Salary Slip"),
        ("DocType", "Salary Structure"),
        ("DocType", "Salary Structure Assignment"),
        ("DocType", "Salary Component"),
        ("DocType", "Additional Salary"),
    )),
    ("Reports", (
        ("Report", "Monthly Attendance Sheet"),
        ("Report", "Employee Leave Balance"),
        ("Report", "Employee Leave Balance Summary"),
        ("Report", "Salary Register"),
        ("Report", "Salary Payments Based On Payment Mode"),
        ("Report", "Employee Information"),
        ("Report", "Employee Analytics"),
        ("Report", "Department Analytics"),
        ("Report", "Employee Advance Summary"),
        ("Report", "Expense Claim Analytics"),
    )),
)

# Lucide icon names for each left-nav item, keyed by its label.
ICONS = {
    "Dashboard": "gauge",
    "Check in / out": "log-in",
    "Leave Application": "calendar-days",
    "Expense Claim": "receipt",
    "Payroll Entry": "wallet",
    "Employee": "users",
    "Monthly payroll payout": "wallet",
    "Monthly Attendance Sheet": "file-spreadsheet",
    "Employee Leave Balance": "calendar-check",
    "Employee Leave Balance Summary": "calendar-check",
    "Salary Register": "banknote",
    "Salary Payments Based On Payment Mode": "banknote",
    "Employee Information": "id-card",
    "Employee Analytics": "bar-chart-3",
    "Department Analytics": "bar-chart-3",
    "Employee Advance Summary": "hand-coins",
    "Expense Claim Analytics": "bar-chart-3",
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
