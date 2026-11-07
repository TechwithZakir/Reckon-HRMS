from reckon_hrms.constants import TENANT_OWNED_DOCTYPES

app_name = "reckon_hrms"
app_title = "Reckon HRMS"
app_publisher = "Reckon Technologies Ltd"
app_description = "Compact, company-wise SaaS HRMS and payroll"
app_email = ""
app_license = "GPL-3.0-or-later"

# Frappe HRMS is the engine. The SaaS platform provides tenants and companies.
required_apps = ["frappe", "erpnext", "hrms", "reckon_saas_platform"]

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
        "before_validate": "reckon_saas_platform.tenant_security.bind_doc_to_tenant",
        "validate": [
            "reckon_saas_platform.tenant_security.validate_tenant_company_immutable",
            "reckon_saas_platform.tenant_security.validate_tenant_owned_doc",
        ],
    }
    for doctype in TENANT_OWNED_DOCTYPES
}
