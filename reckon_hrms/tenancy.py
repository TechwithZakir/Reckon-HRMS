"""Company-wise tenancy for Reckon HRMS.

A tenant user has Company User Permissions (created by reckon_saas_platform).
Frappe applies those to list views and links; these conditions are the
server-side second layer so direct API calls cannot read another Company.
"""

ADMIN_ROLES = frozenset({"Administrator", "System Manager"})


def _quote(value):
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def build_company_condition(table, companies):
    """Return a SQL condition limiting ``table`` to ``companies``.

    An empty list matches nothing, so a user without a Company sees no rows.
    """
    if not companies:
        return "1=0"
    values = ", ".join(_quote(c) for c in sorted(set(companies)))
    return f"`{table}`.`company` in ({values})"


def employee_query_conditions(user=None):
    """permission_query_conditions hook for Employee."""
    import frappe

    user = user or frappe.session.user
    if user == "Administrator" or ADMIN_ROLES.intersection(frappe.get_roles(user)):
        return ""
    companies = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": "Company"},
        pluck="for_value",
    )
    return build_company_condition("tabEmployee", companies)
