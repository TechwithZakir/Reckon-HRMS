"""Page 2 (Salary rules) back end, read side for this slice: tax slabs, pay items, structures and
the people who still lack a structure. Writes (save component, bulk assign, payslip preview) come next.

Every read is permission-checked and paged (max 100 rows).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, get_first_day, getdate

from reckon_hrms.api.scope import own_employee
from reckon_hrms.api.shortcuts import route
from reckon_hrms.paging import DEFAULT_PAGE, page_bounds
from reckon_hrms.salary_formula import describe

SALARY_ROLES = ["HR Manager", "HR User", "Payroll Manager", "System Manager"]


def _mine() -> str:
    from reckon_hrms.api.home import _company

    return _company()


def _gate(doctype: str):
    frappe.only_for(SALARY_ROLES)
    if not frappe.has_permission(doctype, "read"):
        frappe.throw(_("You do not have permission to read {0}.").format(doctype.lower()),
                     frappe.PermissionError)


def _company_components(mine: str) -> list:
    """The pay items of this company: ones it created, plus any (standard or not) that one of its salary structures uses."""
    used = frappe.db.sql_list(
        "SELECT DISTINCT sd.salary_component FROM `tabSalary Detail` sd JOIN `tabSalary Structure` ss ON ss.name = sd.parent "
        "WHERE sd.parenttype = 'Salary Structure' AND ss.company = %s", (mine,))
    return used


@frappe.whitelist(methods=["GET"])
def list_components(start=0, page_length=DEFAULT_PAGE) -> dict:
    _gate("Salary Component")
    start_i, length_i = page_bounds(start, page_length)
    mine = _mine()
    used = _company_components(mine)
    or_filters = [["company", "=", mine]] + ([["name", "in", used]] if used else [])
    rows = frappe.get_list(
        "Salary Component",
        or_filters=or_filters,
        fields=["name", "type", "salary_component_abbr", "depends_on_payment_days", "is_tax_applicable"],
        order_by="name asc", start=start_i, page_length=length_i,
    )
    return {
        "rows": rows,
        "total": len(frappe.get_list("Salary Component", or_filters=or_filters, pluck="name", limit_page_length=0)),
        "add_new": route("Salary Component", "new"),
        "list": route("Salary Component", "list"),
    }


@frappe.whitelist(methods=["GET"])
def list_structures(company: str | None = None, start=0, page_length=DEFAULT_PAGE) -> dict:
    _gate("Salary Structure")
    start_i, length_i = page_bounds(start, page_length)
    # The company argument is ignored: structures listed and counted are always the signed-in person's own company.
    filters = {"company": _mine()}
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
    filters = {"company": _mine()}  # a company sent by the page is ignored
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
    company = _mine()  # never a company the page sends
    employee_filters = {"status": "Active", "company": company}
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
        "currency": frappe.db.get_value("Company", company, "default_currency") or "",
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

    labels: dict[str, str] = {}

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
                labels[row.abbr] = row.salary_component
            how = describe(row.formula, row.amount_based_on_formula, labels, row.condition)
            out.append({"component": row.salary_component, "abbr": row.abbr, "amount": amount, "how": how})
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


def structure_amounts(structure: str, base) -> dict:
    """Basic, additions, gross and deductions for a base salary, for the run list.

    Same formula engine as the payslip preview. Income tax is not included: it is worked out on the slip.
    """
    from hrms.payroll.utils import COMPONENT_EVAL_GLOBALS, _safe_eval

    base_amount = flt(base)
    doc = frappe.get_cached_doc("Salary Structure", structure)
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
            out.append((row.salary_component, amount))
        return out

    earnings = compute(doc.earnings)
    deductions = compute(doc.deductions)
    basic = sum(amount for component, amount in earnings if component == "Basic Salary")
    gross = round(sum(amount for _component, amount in earnings), 2)
    lines = [(c, "Earning", a) for c, a in earnings] + [(c, "Deduction", a) for c, a in deductions]
    return {"basic": round(basic, 2), "additions": round(gross - basic, 2), "gross": gross,
            "deductions": round(sum(amount for _component, amount in deductions), 2), "lines": lines}


BULK_BATCH = 200


def assign_one(employee: str, structure: str, base: float, from_date, company: str):
    """Give one person a structure and their own gross from a date. A new assignment, so earlier slips and history stay as they were."""
    ssa = frappe.get_doc({"doctype": "Salary Structure Assignment", "employee": employee, "salary_structure": structure,
                          "from_date": from_date, "base": base, "company": company})
    ssa.insert(ignore_permissions=True)
    ssa.submit()
    return ssa.name


def _latest_assignment(employee: str, on):
    return frappe.db.get_value(
        "Salary Structure Assignment", {"employee": employee, "docstatus": 1, "from_date": ["<=", on]},
        ["name", "salary_structure", "base", "from_date"], as_dict=True, order_by="from_date desc, creation desc")


@frappe.whitelist(methods=["GET"])
def employee_pay(start=0, page_length=25, search: str | None = None) -> dict:
    """Active people of this company with their current structure and gross, for the gross salary table."""
    _gate("Salary Structure Assignment")
    mine = _mine()
    start_i, length_i = page_bounds(start, page_length)
    filters = {"company": mine, "status": "Active"}
    or_filters = None
    if search:
        like = f"%{str(search).strip()[:60]}%"
        or_filters = [["employee_name", "like", like], ["name", "like", like], ["designation", "like", like]]
    total = len(frappe.get_all("Employee", filters=filters, or_filters=or_filters, pluck="name", limit_page_length=0))
    people = frappe.get_all("Employee", filters=filters, or_filters=or_filters, fields=["name", "employee_name", "designation"],
                            order_by="employee_name asc", start=start_i, page_length=length_i)
    today = frappe.utils.nowdate()
    rows = []
    for person in people:
        current = _latest_assignment(person.name, today) or {}
        rows.append({**person, "structure": current.get("salary_structure") or "", "base": float(current.get("base") or 0),
                     "from_date": str(current.get("from_date") or "")})
    structures = frappe.get_all("Salary Structure", filters={"company": mine, "docstatus": 1, "is_active": "Yes"}, pluck="name", order_by="name asc")
    return {"rows": rows, "total": total, "structures": structures, "currency": frappe.db.get_value("Company", mine, "default_currency") or ""}


@frappe.whitelist(methods=["POST"])
def set_gross(rows, from_date: str | None = None) -> dict:
    """Set each person's own gross salary (and structure): a new Salary Structure Assignment per changed person. Up to 100 a call."""
    frappe.only_for(["HR Manager", "Payroll Manager", "System Manager"])
    if not frappe.has_permission("Salary Structure Assignment", "create"):
        frappe.throw(_("You do not have permission to assign salary structures."), frappe.PermissionError)
    from reckon_hrms.importer import parse_amount

    mine = _mine()
    rows = frappe.parse_json(rows) if isinstance(rows, str) else rows
    if not isinstance(rows, list) or not rows:
        frappe.throw(_("Nothing to save."))
    on = getdate(from_date) if from_date else get_first_day(getdate(frappe.utils.nowdate()))
    out = {"created": 0, "unchanged": 0, "failed": []}
    for row in rows[:100]:
        employee = str((row or {}).get("employee") or "")
        try:
            own_employee(employee)
            amount = parse_amount(row.get("gross"))
            if amount is None:
                raise ValueError(_("Gross must be a monthly amount above 0."))
            structure = str(row.get("structure") or "")
            if not frappe.db.exists("Salary Structure", {"name": structure, "company": mine, "docstatus": 1}):
                raise ValueError(_("Choose one of your submitted salary structures."))
            joined = frappe.db.get_value("Employee", employee, "date_of_joining")
            start = max(on, getdate(joined)) if joined else on
            current = _latest_assignment(employee, start)
            if current and current.salary_structure == structure and abs(float(current.base or 0) - amount) < 0.005:
                out["unchanged"] += 1
                continue
            if frappe.db.exists("Salary Structure Assignment", {"employee": employee, "docstatus": 1, "from_date": start}):
                raise ValueError(_("This person already has an assignment from {0}. Choose a later date.").format(start))
            assign_one(employee, structure, amount, start, mine)
            out["created"] += 1
        except Exception as exc:  # noqa: BLE001 - one person's problem must not stop the others
            out["failed"].append({"employee": employee, "reason": str(exc)[:160]})
    frappe.db.commit()
    return out


@frappe.whitelist(methods=["POST"])
def bulk_assign(structure: str, base, from_date: str, company: str | None = None) -> dict:
    """Give a structure and base to every active person without one. Runs in the background.

    Idempotent: people who already have this structure from this date are skipped, not doubled.
    Returns a job id; poll get_bulk_progress with it.
    """
    frappe.only_for(["HR Manager", "Payroll Manager", "System Manager"])
    if not frappe.has_permission("Salary Structure Assignment", "create"):
        frappe.throw(_("You do not have permission to assign salary structures."), frappe.PermissionError)
    # Always the signed-in person's own company: a company sent by the page is ignored, so no other company's people are touched.
    company = _mine()
    if not frappe.db.exists("Salary Structure", {"name": structure, "docstatus": 1, "company": company}):
        frappe.throw(_("Choose a submitted salary structure."))
    if flt(base) <= 0:
        frappe.throw(_("Base salary must be above zero."))
    job_id = frappe.generate_hash(length=10)
    frappe.cache().set_value(f"reckon_bulk:{job_id}", {"state": "queued", "created": 0, "skipped": 0,
                                                        "failed": [], "done": 0, "total": 0})
    frappe.enqueue(
        "reckon_hrms.api.salary.run_bulk_assign", queue="long", timeout=3600, job_id=job_id,
        structure=structure, base=flt(base), from_date=from_date, company=company, job=job_id,
    )
    return {"job": job_id}


def run_bulk_assign(structure, base, from_date, company, job):
    """Background worker: assign in batches of 200 and publish progress after each batch."""
    key = f"reckon_bulk:{job}"
    filters = {"status": "Active"}
    if company:
        filters["company"] = company
    people = frappe.get_all("Employee", filters=filters, pluck="name", order_by="name asc", limit_page_length=0)
    have = set(frappe.get_all(
        "Salary Structure Assignment", filters={"docstatus": 1, "from_date": ["<=", from_date],
                                                "employee": ["in", people]} if people else {"name": ""},
        pluck="employee", limit_page_length=0,
    ))
    todo = [p for p in people if p not in have]
    state = {"state": "running", "created": 0, "skipped": len(people) - len(todo), "failed": [],
             "done": 0, "total": len(todo)}
    for i in range(0, len(todo), BULK_BATCH):
        for emp in todo[i:i + BULK_BATCH]:
            try:
                ssa = frappe.get_doc({"doctype": "Salary Structure Assignment", "employee": emp,
                                      "salary_structure": structure, "from_date": from_date, "base": base,
                                      "company": frappe.db.get_value("Employee", emp, "company")})
                ssa.insert(ignore_permissions=True)
                ssa.submit()
                state["created"] += 1
            except Exception as exc:
                state["failed"].append({"employee": emp, "reason": str(exc)[:160]})
            state["done"] += 1
        frappe.cache().set_value(key, state)
        frappe.publish_realtime("reckon_progress", dict(state, job=job), user=frappe.session.user)
        frappe.db.commit()
    state["state"] = "done"
    frappe.cache().set_value(key, state)
    frappe.publish_realtime("reckon_progress", dict(state, job=job), user=frappe.session.user)


@frappe.whitelist(methods=["GET"])
def get_bulk_progress(job: str) -> dict:
    frappe.only_for(["HR Manager", "Payroll Manager", "System Manager"])
    return frappe.cache().get_value(f"reckon_bulk:{job}") or {"state": "unknown"}
