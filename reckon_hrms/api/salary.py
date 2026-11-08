"""Page 2 (Salary rules) back end, read side for this slice: tax slabs, pay items, structures and
the people who still lack a structure. Writes (save component, bulk assign, payslip preview) come next.

Every read is permission-checked and paged (max 100 rows).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

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


@frappe.whitelist(methods=["GET"])
def preview_payslip(structure: str, base) -> dict:
    """Earnings and deductions for a base salary, worked out with HRMS's own formula engine.

    Uses the same evaluator as Salary Slip (hrms.payroll.utils._safe_eval with its globals). Nothing is
    saved. Tax is not in this preview: it is worked out on the real slip.
    """
    _gate("Salary Structure")
    from hrms.payroll.utils import COMPONENT_EVAL_GLOBALS, _safe_eval

    base_amount = flt(base)
    if base_amount < 0:
        frappe.throw(_("Base salary cannot be negative."))
    doc = frappe.get_doc("Salary Structure", structure)
    data = {"base": base_amount}
    globals_ = dict(COMPONENT_EVAL_GLOBALS)

    def compute(rows):
        out = []
        for row in rows:
            if row.condition and not _safe_eval(row.condition, globals_, dict(data)):
                continue
            if row.amount_based_on_formula and row.formula:
                amount = flt(_safe_eval(row.formula, globals_, dict(data)), 2)
            else:
                amount = flt(row.amount, 2)
            if row.abbr:
                data[row.abbr] = amount
            out.append({"component": row.salary_component, "abbr": row.abbr, "amount": amount})
        return out

    earnings = compute(doc.earnings)
    deductions = compute(doc.deductions)
    gross = round(sum(r["amount"] for r in earnings), 2)
    total_deductions = round(sum(r["amount"] for r in deductions), 2)
    return {
        "structure": doc.name,
        "base": base_amount,
        "earnings": earnings,
        "deductions": deductions,
        "gross": gross,
        "total_deductions": total_deductions,
        "take_home_before_tax": round(gross - total_deductions, 2),
        "note": _("Income tax is worked out on the real salary slip, not in this preview."),
    }
