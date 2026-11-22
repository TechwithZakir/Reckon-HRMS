"""Page 1 (Your company) back end: tap-to-add lists of offices, departments, job titles, levels and
types of employee, with usage counts and safe delete.

Lists are server-paged (max 100 rows). Creating is idempotent. Deleting is refused while employees
use the record, and the message says how many.
"""

from __future__ import annotations

import frappe
from frappe import _

from reckon_hrms.api.shortcuts import route
from reckon_hrms.paging import DEFAULT_PAGE, page_bounds

# DocType -> (Employee field that links to it, plain-language label, name field on the DocType)
CHIP_TYPES = {
    "Branch": ("branch", "Offices and factories", "branch"),
    "Department": ("department", "Departments", "department_name"),
    "Designation": ("designation", "Job titles", "designation_name"),
    "Employee Grade": ("grade", "Levels", "name"),
    "Employment Type": ("employment_type", "Types of employee", "employee_type_name"),
}

SETUP_ROLES = ["HR Manager", "HR User", "System Manager"]


def _chip_type(doctype: str) -> tuple[str, str, str]:
    if doctype not in CHIP_TYPES:
        frappe.throw(_("This list cannot be changed here."), frappe.PermissionError)
    return CHIP_TYPES[doctype]


def _check(doctype: str, ptype: str):
    if not frappe.has_permission(doctype, ptype):
        frappe.throw(_("You do not have permission to {0} {1}.").format(ptype, doctype.lower()),
                     frappe.PermissionError)


def _mine() -> str:
    """The signed-in person's own company. Every list, count and delete here is limited to it, never to what the client sends."""
    from reckon_hrms.api.home import _company

    return _company()


def _own_filters(doctype: str, company: str) -> dict:
    """Only this company's records: a branch, department, job title, level or type added by another company is never listed."""
    return {"company": company} if frappe.get_meta(doctype).has_field("company") else {}


def usage_counts(doctype: str, names: list[str], company: str | None = None) -> dict[str, int]:
    """How many of this company's employees use each record. One grouped query, not one per row."""
    if not names:
        return {}
    field, _label, _name = _chip_type(doctype)  # field comes from the allow-list, never from input
    company = company or _mine()
    rows = frappe.db.sql(
        f"SELECT `{field}`, COUNT(`name`) FROM `tabEmployee` "
        f"WHERE `{field}` IN %(names)s AND `company` = %(company)s GROUP BY `{field}`",
        {"names": tuple(names), "company": company},
    )
    return {name: int(n) for name, n in rows}


@frappe.whitelist(methods=["GET"])
def list_items(doctype: str, start=0, page_length=DEFAULT_PAGE, company: str | None = None) -> dict:
    _field, _label, name_field = _chip_type(doctype)
    _check(doctype, "read")
    start_i, length_i = page_bounds(start, page_length)
    # The company argument is ignored: the list is always the signed-in person's own company.
    mine = _mine()
    filters = _own_filters(doctype, mine)
    total = frappe.db.count(doctype, filters)
    rows = frappe.get_list(doctype, filters=filters, fields=["name", name_field], order_by=f"{name_field} asc",
                           start=start_i, page_length=length_i)
    names = [r.name for r in rows]
    used = usage_counts(doctype, names, mine)
    return {
        "rows": [{"name": r.name, "label": r.get(name_field) or r.name, "employees": used.get(r.name, 0)} for r in rows],
        "total": total,
        "start": start_i,
        "page_length": length_i,
        "add_new": route(doctype, "new"),
        "list": route(doctype, "list"),
    }


@frappe.whitelist(methods=["POST"])
def create_item(doctype: str, name: str, company: str | None = None) -> dict:
    """Create one chip. Idempotent: an existing record with the same name is returned."""
    _chip_type(doctype)
    _check(doctype, "create")
    clean = (name or "").strip()
    if not clean or len(clean) > 140:
        frappe.throw(_("Type a name between 1 and 140 characters."))

    _field, _label, name_field = CHIP_TYPES[doctype]
    if doctype == "Department":
        if not company:
            frappe.throw(_("Choose the company for this department."))
        existing = frappe.db.get_value("Department", {"department_name": clean, "company": company}, "name")
        if existing:
            return {"name": existing, "created": False}
        doc = frappe.get_doc({"doctype": "Department", "department_name": clean, "company": company})
    elif doctype == "Employee Grade":
        if frappe.db.exists("Employee Grade", clean):
            return {"name": clean, "created": False}
        doc = frappe.get_doc({"doctype": "Employee Grade", "__newname": clean})
    else:
        if frappe.db.exists(doctype, clean):
            return {"name": clean, "created": False}
        doc = frappe.get_doc({"doctype": doctype, name_field: clean})
    doc.insert()
    return {"name": doc.name, "created": True}


@frappe.whitelist(methods=["POST"])
def delete_item(doctype: str, name: str) -> dict:
    """Delete one chip. Refused, with the count, while employees use it."""
    _field, _label, _name = _chip_type(doctype)
    _check(doctype, "delete")
    mine = _mine()
    owner = frappe.db.get_value(doctype, name, "company") if frappe.get_meta(doctype).has_field("company") else mine
    if owner != mine:
        frappe.throw(_("This record does not belong to your company."), frappe.PermissionError)
    used = usage_counts(doctype, [name], mine).get(name, 0)
    if used:
        frappe.throw(_("{0} is used by {1} employee(s). Move those employees first.").format(name, used))
    frappe.delete_doc(doctype, name)
    return {"name": name, "deleted": True}


@frappe.whitelist(methods=["GET"])
def get_state() -> dict:
    """Checklist from this company's own records, not clicks and not other companies' data."""
    frappe.only_for(SETUP_ROLES)
    mine = _mine()
    counts = {dt: frappe.db.count(dt, _own_filters(dt, mine)) for dt in CHIP_TYPES}
    employees = frappe.db.count("Employee", {"company": mine})
    holiday_lists = frappe.db.count("Holiday List", {"company": mine})
    leave = frappe.db.count("Leave Policy", {"company": mine}) + (
        frappe.db.count("Leave Type", {"company": mine}) if frappe.get_meta("Leave Type").has_field("company") else 0)
    steps = [
        {"key": "company", "label": _("Company details"), "done": bool(frappe.db.get_value("Company", mine, "country"))},
        {"key": "industry", "label": _("Industry (in Guided setup)"), "done": bool(frappe.db.get_value("Company", mine, "reckon_industry"))},
        {"key": "offices", "label": _("Offices and departments"),
         "done": counts["Branch"] > 0 and counts["Department"] > 0},
        {"key": "job_titles", "label": _("Job titles"), "done": counts["Designation"] > 0},
        {"key": "people", "label": _("Add your people"), "done": employees > 0},
        {"key": "holidays", "label": _("Holidays and leave"), "done": holiday_lists > 0 and leave > 0},
        {"key": "attendance", "label": _("Attendance"), "done": frappe.db.count("Shift Type", {"company": mine}) > 0},
    ]
    done = sum(1 for s in steps if s["done"])
    return {
        "steps": steps,
        "done": done,
        "total": len(steps),
        "percent": round(100 * done / len(steps)),
        "counts": counts,
        "employees": employees,
    }
