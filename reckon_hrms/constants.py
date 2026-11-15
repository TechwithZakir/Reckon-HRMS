"""Static Reckon HRMS definitions. No Frappe import, so these stay unit-testable."""

MODULE_KEY = "hrms"
MODULE_LABEL = "Reckon HRMS"
WORKSPACE = "app/reckon-hrms"
HOME_ROUTE = "/hrms-home"

ADMIN_ROLE = "Reckon HRMS Admin"
ROLES = (
    "Reckon HRMS Admin",
    "Reckon HRMS Manager",
    "Reckon HRMS Employee",
)

# Version 1 modules and the subscription feature each one turns on.
MODULE_FEATURES = {
    "employees": "Employees",
    "attendance_shifts": "Attendance & Shifts",
    "leave": "Leave",
    "payroll": "Payroll",
}

# Company-owned HRMS doctypes. Each has a real Company link, so the platform's
# tenant query, permission check and company binding apply to it.
TENANT_OWNED_DOCTYPES = (
    "Employee",
    "Attendance",
    "Leave Application",
    "Salary Structure",
    "Salary Structure Assignment",
    "Salary Slip",
    "Payroll Entry",
    "Expense Claim",
    # Holiday lists get a Company field (patch), so each tenant has its own calendar.
    "Holiday List",
    # Office coordinates for the attendance geofence, one per company.
    "HRMS Office Location",
    # A company's ZKTeco / ZKBio Time device and its punch sync.
    "HRMS Attendance Device",
)


def tenant_role(kind: str, company: str) -> str:
    """Per-tenant role name, for example "Reckon HRMS Admin - Acme Ltd". kind is "Admin" or "User"."""
    if kind not in {"Admin", "User"}:
        raise ValueError(f"unknown HRMS role kind: {kind}")
    return f"Reckon HRMS {kind} - {company}"[:140]

# Desk reach for a tenant on the compact HRMS module: its four modules and their masters.
DESK_GUARD = True
DESK_DOCTYPES = TENANT_OWNED_DOCTYPES + (
    "Leave Type",
    "Leave Policy",
    "Holiday List",
    "Shift Type",
    "Shift Assignment",
    "Salary Component",
    "Additional Salary",
    "Employee Checkin",
    # Everything the left menu offers must be reachable, or the tenant meets "not available in your workspace".
    "Holiday List Assignment",
    "Leave Allocation",
    "Expense Claim Type",
    "Department",
    "Designation",
)
DESK_WORKSPACES = ("Reckon HRMS",)

# Custom Desk pages (the setup flow links between them) and the reports the menu lists.
DESK_PAGES = (
    "reckon-hrms-home",
    "reckon-hrms-hr-studio",
    "reckon-hrms-setup",
    "reckon-hrms-checkin",
    "reckon-hrms-company",
    "reckon-hrms-salary",
    "reckon-hrms-run",
    "reckon-hrms-payout",
    "query-report",
    "print",
)
