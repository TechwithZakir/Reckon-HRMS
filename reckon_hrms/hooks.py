from reckon_hrms.constants import READ_ONLY_SETTINGS, SHARED_CATALOG_DOCTYPES, TENANT_OWNED_DOCTYPES

app_name = "reckon_hrms"
app_title = "Reckon HRMS"
app_publisher = "Reckon Technologies Ltd"
app_description = "Compact, company-wise SaaS HRMS and payroll"
app_email = ""
app_license = "GPL-3.0-or-later"

# Frappe HRMS is the engine. The SaaS platform provides tenants and companies.
required_apps = ["frappe", "erpnext", "hrms", "reckon_saas_platform"]

# Shared stage code for the single Setup page (Your company, Salary rules, Run salary).
app_include_js = ["/assets/reckon_hrms/js/reckon_setup_stages.js", "/assets/reckon_hrms/js/reckon_home_redirect.js"]

# The Reckon HRMS tile on the Desk apps screen, and the landing page for HRMS-only tenants.
add_to_apps_screen = [
    {
        "name": "reckon_hrms",
        "logo": "/assets/reckon_hrms/images/reckon-hrms.svg",
        "title": "Reckon HRMS",
        "route": "/desk/reckon-hrms/reckon-hrms-overview",
        "has_permission": "reckon_hrms.desk.can_see_app",
    }
]

# Registers Reckon HRMS as a SaaS module, the same way Distribution does.
reckon_saas_modules = [
    "reckon_hrms.saas_module.get_module_definition",
]

# Tenant users see only their Company's rows. Same platform rules as Distribution.
permission_query_conditions = {
    doctype: "reckon_saas_platform.tenant_security.get_tenant_owned_query"
    for doctype in TENANT_OWNED_DOCTYPES
}
has_permission = {
    doctype: "reckon_saas_platform.tenant_security.has_tenant_owned_permission"
    for doctype in TENANT_OWNED_DOCTYPES
}
# Reference masters: the vendor's seeded rows are a read-only catalog; a tenant's own rows are its alone.
permission_query_conditions.update({
    doctype: "reckon_saas_platform.tenant_security.get_tenant_shared_query" for doctype in SHARED_CATALOG_DOCTYPES
})
has_permission.update({
    doctype: "reckon_saas_platform.tenant_security.has_tenant_shared_permission" for doctype in SHARED_CATALOG_DOCTYPES
})
# Vendor-wide settings: read-only for tenants (single records, so no row filter is needed).
for _settings in READ_ONLY_SETTINGS:
    has_permission[_settings] = "reckon_hrms.tenancy_hooks.read_only_permission"
# Rows that name another record are scoped through it.
permission_query_conditions["Holiday List Assignment"] = "reckon_hrms.tenancy_hooks.holiday_assignment_query"
has_permission["Holiday List Assignment"] = "reckon_hrms.tenancy_hooks.holiday_assignment_permission"
permission_query_conditions["Employee Checkin"] = "reckon_hrms.tenancy_hooks.employee_linked_query"
has_permission["Employee Checkin"] = "reckon_hrms.tenancy_hooks.employee_linked_permission"
doc_events = {
    doctype: {
        "before_validate": "reckon_hrms.tenancy_hooks.bind_company",
        "validate": [
            "reckon_hrms.tenancy_hooks.validate_company_immutable",
            "reckon_hrms.tenancy_hooks.validate_owned",
        ],
    }
    for doctype in TENANT_OWNED_DOCTYPES
}
# A tenant's own addition to a shared master is stamped with its company (vendor and seed writes stay unstamped).
for _doctype in SHARED_CATALOG_DOCTYPES:
    doc_events[_doctype] = {"before_validate": "reckon_hrms.tenancy_hooks.bind_catalog_company"}

# A slip gives its components the company's accounts, after HRMS has added any tax components, so submitting it
# and booking the payroll run find an account for every line.
doc_events["Salary Slip"]["validate"] = [
    *doc_events["Salary Slip"]["validate"], "reckon_hrms.component_accounts.ensure_component_accounts",
]
doc_events["Salary Slip"]["before_submit"] = "reckon_hrms.component_accounts.ensure_component_accounts"

# Tenant User Assignment access is reconciled by the platform (reckon_saas_platform.team).

# Self-service scope: a self-service login sees only its own employee record.
doc_events.setdefault("Tenant User Assignment", {}).update({
    "after_insert": ["reckon_hrms.access.sync_self_service"],
    "on_update": ["reckon_hrms.access.sync_self_service"],
})
doc_events.setdefault("Employee", {}).update({
    "after_insert": ["reckon_hrms.access.sync_employee_self_service", "reckon_hrms.tenancy_hooks.ensure_holiday_assignment"],
    "on_update": ["reckon_hrms.access.sync_employee_self_service"],
})


# The check-in page lives at /hrms-checkin. Frappe cannot load a hyphenated www module, so the file is named hrms_checkin.
website_route_rules = [
    {"from_route": "/hrms-checkin", "to_route": "hrms_checkin"},
    {"from_route": "/hrms-home", "to_route": "hrms_home"},
]


# Biometric devices: every minute, queue a punch sync for each enabled ZKTeco / ZKBio Time device that is due.
scheduler_events = {
    "cron": {
        "* * * * *": ["reckon_hrms.reckon_hrms.doctype.hrms_attendance_device.hrms_attendance_device.run_due_devices"],
    },
}

# The Frappe HR mobile app (the installable web app at /hrms) carries the Reckon HRMS name, icons and manifest.
after_request = ["reckon_hrms.pwa.rebrand_response"]
