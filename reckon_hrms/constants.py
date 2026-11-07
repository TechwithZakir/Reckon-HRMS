"""Static Reckon HRMS definitions. No Frappe import, so these stay unit-testable."""

MODULE_KEY = "hrms"
MODULE_LABEL = "Reckon HRMS"
WORKSPACE = "app/reckon-hrms"
HOME_ROUTE = "/desk/reckon-hrms"

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
)


def tenant_role(kind: str, company: str) -> str:
    """Per-tenant role name, for example "Reckon HRMS Admin - Acme Ltd". kind is "Admin" or "User"."""
    if kind not in {"Admin", "User"}:
        raise ValueError(f"unknown HRMS role kind: {kind}")
    return f"Reckon HRMS {kind} - {company}"[:140]
