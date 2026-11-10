"""Reckon HRMS menu: one definition for the desk left nav, the cards and the web pages.

Items: ("DocType", name) | ("Report", name) | ("Page", page_name, label). Icons are Lucide names.
Reports or DocTypes that do not exist on a site are skipped when the menu is built.

Each item appears once. HR Studio and Payroll Studio are one page each, with steps.
The old "Monthly payroll payout" page is not listed: Run salary does that job.
"""

# Labels shown in the left nav for DocTypes whose record name is technical.
DOCTYPE_LABELS = {"HRMS Office Location": "Office Location"}

# Employee Checkin is not in the menu: staff check in from Check in / out, which records it.
# Each item appears once, so the left nav and the cards stay in step.
MENU = (
    ("HR Studio", (
        ("Page", "reckon-hrms-hr-studio", "HR Studio"),
    )),
    ("Payroll Studio", (
        ("Page", "reckon-hrms-setup", "Payroll Studio"),
    )),
    ("Dashboard", (
        ("Page", "reckon-hrms-home", "Dashboard"),
    )),
    ("People", (
        ("DocType", "Employee"),
        ("DocType", "Department"),
        ("DocType", "Designation"),
        ("DocType", "HRMS Office Location"),  # shown as Office Location
    )),
    ("Time & Attendance", (
        ("Page", "reckon-hrms-checkin", "Check in / out"),
        ("DocType", "Attendance"),
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
        ("DocType", "Payroll Entry"),
        ("DocType", "Salary Slip"),
        ("DocType", "Salary Structure"),
        ("DocType", "Salary Structure Assignment"),
        ("DocType", "Salary Component"),
        ("DocType", "Additional Salary"),
    )),
    ("HR Reports", (
        ("Report", "Employee Information"),
        ("Report", "Employee Analytics"),
        ("Report", "Employee Birthday"),
        ("Report", "Employee Exits"),
        ("Report", "Employee Advance Summary"),
        ("Report", "Monthly Attendance Sheet"),
        ("Report", "Shift Attendance"),
        ("Report", "Employees working on a holiday"),
        ("Report", "Employee Leave Balance"),
        ("Report", "Employee Leave Balance Summary"),
        ("Report", "Leave Ledger"),
        ("Report", "Unpaid Expense Claim"),
    )),
    ("Payroll Reports", (
        ("Report", "Salary Register"),
        ("Report", "Salary Payments Based On Payment Mode"),
        ("Report", "Salary Payments via ECS"),
        ("Report", "Bank Remittance"),
        ("Report", "Employee CTC Break-up"),
        ("Report", "Accrued Earnings Report"),
        ("Report", "Income Tax Computation"),
        ("Report", "Income Tax Deductions"),
        ("Report", "Professional Tax Deductions"),
        ("Report", "Provident Fund Deductions"),
    )),
)

# Lucide icon names for each left-nav item, keyed by its label.
ICONS = {
    "HR Studio": "users",
    "Payroll Studio": "wallet",
    "Dashboard": "gauge",
    "Check in / out": "log-in",
    "Employee": "users",
    "Department": "building-2",
    "Designation": "id-card",
    "Office Location": "map-pin",
    "Attendance": "user-check",
    "Employee Checkin": "fingerprint",
    "Shift Type": "clock",
    "Shift Assignment": "timer",
    "Holiday List": "calendar-off",
    "Holiday List Assignment": "calendar-range",
    "Leave Application": "calendar-days",
    "Leave Type": "tag",
    "Leave Allocation": "plus-circle",
    "Expense Claim": "receipt",
    "Expense Claim Type": "list",
    "Payroll Entry": "wallet",
    "Salary Slip": "file-text",
    "Salary Structure": "layers",
    "Salary Structure Assignment": "link",
    "Salary Component": "puzzle",
    "Additional Salary": "plus",
    "Employee Information": "id-card",
    "Employee Analytics": "bar-chart-3",
    "Employee Birthday": "cake",
    "Employee Exits": "door-open",
    "Employee Advance Summary": "hand-coins",
    "Monthly Attendance Sheet": "file-spreadsheet",
    "Shift Attendance": "file-spreadsheet",
    "Employees working on a holiday": "calendar-off",
    "Employee Leave Balance": "calendar-check",
    "Employee Leave Balance Summary": "calendar-check",
    "Leave Ledger": "book-open",
    "Unpaid Expense Claim": "receipt",
    "Salary Register": "banknote",
    "Salary Payments Based On Payment Mode": "banknote",
    "Salary Payments via ECS": "banknote",
    "Bank Remittance": "landmark",
    "Employee CTC Break-up": "file-text",
    "Accrued Earnings Report": "file-text",
    "Income Tax Computation": "calculator",
    "Income Tax Deductions": "calculator",
    "Professional Tax Deductions": "calculator",
    "Provident Fund Deductions": "piggy-bank",
}
