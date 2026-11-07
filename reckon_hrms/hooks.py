app_name = "reckon_hrms"
app_title = "Reckon HRMS"
app_publisher = "Reckon Technologies Ltd"
app_description = "Compact, company-wise SaaS HRMS and payroll"
app_email = ""
app_license = "GPL-3.0-or-later"

# Frappe HRMS is the engine; Reckon HRMS rebrands and trims it.
required_apps = ["frappe", "erpnext", "hrms"]

# Version 1 modules shown to users. Other HRMS modules stay installed but hidden.
reckon_hrms_modules = ["Employees", "Attendance & Shifts", "Leave", "Payroll"]

# Company-scoped access: tenant users see only their own Company's records.
permission_query_conditions = {
    "Employee": "reckon_hrms.tenancy.employee_query_conditions",
}
