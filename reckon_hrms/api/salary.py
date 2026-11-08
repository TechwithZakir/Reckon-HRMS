"""Page 2 (Salary rules) back end, read side for this slice: tax slabs, pay items, structures and
the people who still lack a structure. Writes (save component, bulk assign, payslip preview) come next.

Every read is permission-checked and paged (max 100 rows).
"""

from __future__ import annotations

import frappe
from frappe import _

from reckon_hrms.api.shortcuts import route
from reckon_hrms.paging import DEFAULT_PAGE, page_bounds

SALARY_ROLES = ["HR Manager", "HR User", "Payroll Manager", "System Manager"]


def _gate(doctype: str):
    frappe.only_for(SALARY_ROLES)
    if not frappe.has_permission(doctype, "read"):
        frappe.throw(_("You do not have permission to read {0}.").format(doctype.lower()),
                     frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def list_components(start=0, page_length=DEFAULT_PAGE) -> dict:
    _gate("Salary Component")
    start_i, length_i = page_bounds(start, page_length)
    rows = frappe.get_list(
        "Salary Component",
        fields=["name", "type", "salary_component_abbr", "depends_on_payment_days", "is_tax_applicable"],
        order_by="name asc", start=start_i, page_length=length_i,
    )
    return {
        "rows": rows,
        "total": frappe.db.count("Salary Component"),
        "add_new": route("Salary Component", "new"),
        "list": route("Salary Component", "list"),
    }


@frappe.whitelist(methods=["GET"])
def list_structures(company: str | None = None, start=0, page_length=DEFAULT_PAGE) -> dict:
    _gate("Salary Structure")
    start_i, length_i = page_bounds(start, page_length)
    filters = {"company": company} if company else {}
    rows = frappe.get_list(
        "Salary Structure", filters=filters,
        fields=["name", "is_active", "payroll_frequency", "company", "docstatus"],
        order_by="name asc", start=start_i, page_length=length_i,
    )
    names = [r.name for r in rows]
    used = {}
    if names:
        for name, n in frappe.db.sql(
            "SELECT salary_structure, COUNT(DISTINCT employee) FROM `tabSalary Structure Assignment` "
            "WHERE docstatus = 1 AND salary_structure IN %(names)s GROUP BY salary_structure",
            {"names": tuple(names)},
        ):
            used[name] = int(n)
    for r in rows:
        r["people"] = used.get(r.name, 0)
    return {
        "rows": rows,
        "total": frappe.db.count("Salary Structure", filters),
        "add_new": route("Salary Structure", "new"),
        "list": route("Salary Structure", "list"),
    }


@frappe.whitelist(methods=["GET"])
def list_tax_slabs(company: str | None = None, start=0, page_length=DEFAULT_PAGE) -> dict:
    _gate("Income Tax Slab")
    start_i, length_i = page_bounds(start, page_length)
    filters = {"company": company} if company else {}
    rows = frappe.get_list(
        "Income Tax Slab", filters=filters,
        fields=["name", "effective_from", "company", "docstatus"],
        order_by="effective_from desc", start=start_i, page_length=length_i,
    )
    return {
        "rows": rows,
        "total": frappe.db.count("Income Tax Slab", filters),
        "add_new": route("Income Tax Slab", "new"),
        "list": route("Income Tax Slab", "list"),
    }


@frappe.whitelist(methods=["GET"])
def assignment_summary(company: str | None = None) -> dict:
    """How many active people have a structure and how many do not. Counts only, no row list."""
    _gate("Salary Structure Assignment")
    employee_filters = {"status": "Active"}
    if company:
        employee_filters["company"] = company
    active = frappe.db.count("Employee", employee_filters)
    assigned = frappe.db.sql(
        "SELECT COUNT(DISTINCT ssa.employee) FROM `tabSalary Structure Assignment` ssa "
        "JOIN `tabEmployee` e ON e.name = ssa.employee "
        "WHERE ssa.docstatus = 1 AND e.status = 'Active'"
        + (" AND e.company = %(company)s" if company else ""),
        {"company": company} if company else {},
    )[0][0]
    missing = max(0, active - int(assigned))
    return {
        "active": active,
        "with_structure": int(assigned),
        "without_structure": missing,
        "filter_route": route("Salary Structure Assignment", "list"),
    }
