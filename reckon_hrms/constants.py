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
    "Income Tax Slab",
    "Attendance",
    "Leave Application",
    "Salary Structure",
    "Salary Structure Assignment",
    "Salary Slip",
    "Payroll Entry",
    "Expense Claim",
    # Each of these has a Company field; before they were listed here a tenant saw every company's rows.
    "Department",
    "Additional Salary",
    "Shift Assignment",
    "Leave Allocation",
    "Leave Ledger Entry",
    "Leave Policy Assignment",
    "Exit Interview",
    "Employee Benefit Ledger",
    # Holiday lists get a Company field (patch), so each tenant has its own calendar.
    "Holiday List",
    # Office coordinates for the attendance geofence, one per company.
    "HRMS Office Location",
    # A company's ZKTeco / ZKBio Time device and its punch sync.
    "HRMS Attendance Device",
)


# Other HR and payroll doctypes with a Company field. Their lists are limited to the company (tenants) or to the selected
# Default Company (vendor staff), but they are not added to the tenant's compact desk reach (DESK_DOCTYPES).
EXTRA_SCOPED_DOCTYPES = (
    "Appointment Letter",
    "Appraisal",
    "Appraisal Cycle",
    "Arrear",
    "Attendance Request",
    "Employee Advance",
    "Employee Benefit Application",
    "Employee Benefit Claim",
    "Employee Incentive",
    "Employee Onboarding",
    "Employee Onboarding Template",
    "Employee Other Income",
    "Employee Performance Feedback",
    "Employee Promotion",
    "Employee Separation",
    "Employee Separation Template",
    "Employee Tax Exemption Declaration",
    "Employee Tax Exemption Proof Submission",
    "Employee Transfer",
    "Full and Final Statement",
    "Goal",
    "Gratuity",
    "Job Offer",
    "Job Opening",
    "Job Requisition",
    "Leave Block List",
    "Leave Encashment",
    "Leave Period",
    "Overtime Slip",
    "Payroll Correction",
    "Payroll Period",
    "Retention Bonus",
    "Salary Withholding",
    "Shift Request",
    "Shift Schedule Assignment",
    "Staffing Plan",
    "Training Event",
    "Training Program",
    "Travel Request",
)


def tenant_role(kind: str, company: str) -> str:
    """Per-tenant role name, for example "Reckon HRMS Admin - Acme Ltd". kind is "Admin" or "User"."""
    if kind not in {"Admin", "User"}:
        raise ValueError(f"unknown HRMS role kind: {kind}")
    return f"Reckon HRMS {kind} - {company}"[:140]

# Desk reach for a tenant on the compact HRMS module: its four modules and their masters.
DESK_GUARD = True
# Vendor-wide settings forms read for their defaults: tenants read them, only vendor staff change them.
READ_ONLY_SETTINGS = ("HR Settings", "Payroll Settings")

DESK_DOCTYPES = TENANT_OWNED_DOCTYPES + READ_ONLY_SETTINGS + (
    "Branch",
    "Employment Type",
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
    "Employee Grade",
    "Leave Ledger Entry",
    "Exit Interview",
    "Employee Benefit Ledger",
    "Leave Policy Assignment",
)

# Reference masters with no Company of their own. A custom Company field is added to each: the vendor's seeded
# rows (no Company) are a read-only catalog every tenant sees, and a tenant's own additions belong to it alone.
SHARED_CATALOG_DOCTYPES = (
    "Branch",
    "Employment Type",
    "Designation",
    "Employee Grade",
    "Expense Claim Type",
    "Leave Type",
    "Leave Policy",
    "Salary Component",
    "Shift Type",
)

# Rows reached through another record: scoped by that record's Company.
HOLIDAY_ASSIGNMENT = "Holiday List Assignment"
EMPLOYEE_CHECKIN = "Employee Checkin"
DESK_WORKSPACES = ("Reckon HRMS",)

# Custom Desk pages (the setup flow links between them) and the reports the menu lists.
DESK_PAGES = (
    "reckon-hrms-overview",
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
