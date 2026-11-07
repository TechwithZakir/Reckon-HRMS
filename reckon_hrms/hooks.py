from reckon_hrms.constants import TENANT_OWNED_DOCTYPES

app_name = "reckon_hrms"
app_title = "Reckon HRMS"
app_publisher = "Reckon Technologies Ltd"
app_description = "Compact, company-wise SaaS HRMS and payroll"
app_email = ""
app_license = "GPL-3.0-or-later"

# Frappe HRMS is the engine. The SaaS platform provides tenants and companies.
required_apps = ["frappe", "erpnext", "hrms", "reckon_saas_platform"]

# The Reckon HRMS tile on the Desk apps screen, and the landing page for HRMS-only tenants.
add_to_apps_screen = [
    {
        "name": "reckon_hrms",
        "logo": "/assets/reckon_hrms/images/reckon-hrms.svg",
        "title": "Reckon HRMS",
        "route": "/app/reckon-hrms",
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

# Tenant User Assignment access is reconciled by the platform (reckon_saas_platform.team).

