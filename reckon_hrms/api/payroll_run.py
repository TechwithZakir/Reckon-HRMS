"""Page 3 (Run salary) back end, steps 1 and 2: choose month and people, then check the list.

Each step is a stage of the standard Payroll Entry, so a run started here can be continued in the desk.
Steps 3 to 5 (slips, approval, payment) come later. Lists are server-paged (max 100 rows).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_months, flt, get_first_day, get_last_day, getdate

from reckon_hrms.api.home import _company
from reckon_hrms.paging import DEFAULT_PAGE, page_bounds

RUN_ROLES = ["HR Manager", "Payroll Manager", "System Manager"]
FILTER_FIELDS = ("branch", "department", "designation", "grade")


def _gate(doctype: str, ptype: str = "read"):
    frappe.only_for(RUN_ROLES)
    if not frappe.has_permission(doctype, ptype):
        frappe.throw(_("You do not have permission to {0} {1}.").format(ptype, doctype.lower()),
                     frappe.PermissionError)


def _month_bounds(month: str):
    try:
        first = get_first_day(getdate(f"{month}-01"))
    except Exception:
        frappe.throw(_("Choose a month as YYYY-MM."))
    return first, get_last_day(first)


def _has_structure(employee: str, start, end) -> bool:
    return bool(frappe.db.exists("Salary Structure Assignment", {
        "employee": employee, "docstatus": 1, "from_date": ["<=", end]}))


@frappe.whitelist(methods=["POST"])
def start_run(month: str, pay_date: str, branch: str | None = None, department: str | None = None,
              designation: str | None = None, grade: str | None = None) -> dict:
    """Create the draft Payroll Entry for this month, or return the existing draft. Idempotent."""
    _gate("Payroll Entry", "create")
    company = _company()
    start, end = _month_bounds(month)
    existing = frappe.db.get_value("Payroll Entry", {
        "company": company, "start_date": start, "end_date": end, "docstatus": 0}, "name")
    if existing:
        return {"name": existing, "created": False}
    defaults = frappe.db.get_value("Company", company,
                                   ["default_currency", "default_payroll_payable_account"], as_dict=True) or {}
    doc = frappe.get_doc({
        "doctype": "Payroll Entry", "company": company, "payroll_frequency": "Monthly",
        "currency": defaults.get("default_currency"), "exchange_rate": 1,
        "payroll_payable_account": defaults.get("default_payroll_payable_account"),
        "start_date": start, "end_date": end, "posting_date": getdate(pay_date),
        "branch": branch or None, "department": department or None,
        "designation": designation or None, "grade": grade or None,
    })
    doc.insert()
    return {"name": doc.name, "created": True}


@frappe.whitelist(methods=["POST"])
def fetch_employees(name: str) -> dict:
    """Step 2: fill the people list (Get Employees), then report what was found."""
    _gate("Payroll Entry", "write")
    doc = frappe.get_doc("Payroll Entry", name)
    if doc.docstatus != 0:
        frappe.throw(_("This run is no longer a draft."))
    try:
        # HRMS fills doc.employees itself and returns the people with unmarked attendance (warnings).
        unmarked = doc.fill_employee_details() or []
    except frappe.ValidationError as exc:
        frappe.throw(_("No people match these choices. Change the office, department, job title or level."))
    doc.save()
    frappe.db.commit()
    result = get_run(name)
    result["unmarked_attendance"] = len(unmarked)
    return result


@frappe.whitelist(methods=["GET"])
def get_run(name: str) -> dict:
    _gate("Payroll Entry", "read")
    doc = frappe.get_doc("Payroll Entry", name)
    people = [r.employee for r in doc.employees]
    start, end = doc.start_date, doc.end_date
    no_structure = [p for p in people if not _has_structure(p, start, end)]
    slips = frappe.db.count("Salary Slip", {"payroll_entry": name, "docstatus": ["!=", 2]}) if people else 0
    step = 1 if not people else (2 if not slips else 3)
    return {
        "name": doc.name, "status": doc.status, "docstatus": doc.docstatus, "step": step,
        "company": doc.company, "month": str(start)[:7], "pay_date": str(doc.posting_date),
        "included": len(people), "no_structure": len(no_structure), "slips": slips,
        "filters": {f: doc.get(f) for f in FILTER_FIELDS},
        "locked": doc.docstatus != 0,
    }


@frappe.whitelist(methods=["GET"])
def list_people(name: str, filter: str = "all", search: str | None = None, start=0,
                page_length=DEFAULT_PAGE) -> dict:
    """The people table: paged, filtered on the server. Included means "in this run's list"."""
    _gate("Payroll Entry", "read")
    doc = frappe.get_doc("Payroll Entry", name)
    start_i, length_i = page_bounds(start, page_length)
    rows = []
    for r in doc.employees:
        has = _has_structure(r.employee, doc.start_date, doc.end_date)
        status = "ready" if has else "no_structure"
        if filter == "no_structure" and has:
            continue
        if search:
            text = f"{r.employee} {r.employee_name or ''}".lower()
            if search.lower() not in text:
                continue
        rows.append({"employee": r.employee, "employee_name": r.employee_name, "branch": r.get("branch"),
                     "department": r.department, "designation": r.designation, "status": status,
                     "included": True})
    total = len(rows)
    return {"rows": rows[start_i:start_i + length_i], "total": total, "start": start_i,
            "page_length": length_i}


@frappe.whitelist(methods=["POST"])
def exclude_people(name: str, employees: list | str) -> dict:
    """Step 2 only: take people out of the run's list. No slip exists yet, so nothing else changes."""
    _gate("Payroll Entry", "write")
    if isinstance(employees, str):
        employees = frappe.parse_json(employees)
    doc = frappe.get_doc("Payroll Entry", name)
    if doc.docstatus != 0:
        frappe.throw(_("This run is no longer a draft."))
    before = len(doc.employees)
    drop = set(employees or [])
    if drop and frappe.db.exists("Salary Slip", {"payroll_entry": name, "docstatus": 1, "employee": ["in", list(drop)]}):
        frappe.throw(_("A person left out already has a submitted slip. Hold their payment instead."))
    for slip in frappe.get_all("Salary Slip", filters={"payroll_entry": name, "docstatus": 0,
            "employee": ["in", list(drop)]}, pluck="name") if drop else []:
        frappe.delete_doc("Salary Slip", slip, force=True, ignore_permissions=True)
    doc.employees = [r for r in doc.employees if r.employee not in drop]
    doc.save()
    frappe.db.commit()
    return {"removed": before - len(doc.employees), "included": len(doc.employees)}


@frappe.whitelist(methods=["POST"])
def include_people(name: str, employees: list | str) -> dict:
    """Step 2 only: put back people who were left out. Uses the standard employee master data."""
    _gate("Payroll Entry", "write")
    if isinstance(employees, str):
        employees = frappe.parse_json(employees)
    doc = frappe.get_doc("Payroll Entry", name)
    if doc.docstatus != 0:
        frappe.throw(_("This run is no longer a draft."))
    present = {r.employee for r in doc.employees}
    added = 0
    for emp in employees or []:
        if emp in present:
            continue
        row = frappe.db.get_value("Employee", {"name": emp, "company": doc.company, "status": "Active"},
                                  ["employee_name", "department", "designation", "grade"], as_dict=True)
        if not row:
            continue
        doc.append("employees", {"employee": emp, "employee_name": row.employee_name, 
                                 "department": row.department, "designation": row.designation, "grade": row.grade})
        added += 1
    doc.save()
    frappe.db.commit()
    return {"added": added, "included": len(doc.employees)}


SLIP_BATCH = 200


def _slip_args(doc):
    return frappe._dict({
        "salary_slip_based_on_timesheet": doc.salary_slip_based_on_timesheet,
        "payroll_frequency": doc.payroll_frequency, "start_date": doc.start_date, "end_date": doc.end_date,
        "company": doc.company, "posting_date": doc.posting_date,
        "deduct_tax_for_unsubmitted_tax_exemption_proof": doc.deduct_tax_for_unsubmitted_tax_exemption_proof,
        "payroll_entry": doc.name, "exchange_rate": doc.exchange_rate, "currency": doc.currency,
    })


@frappe.whitelist(methods=["POST"])
def create_slips(name: str) -> dict:
    """Step 3: create draft salary slips in background batches of 200, grouped by office."""
    _gate("Payroll Entry", "write")
    doc = frappe.get_doc("Payroll Entry", name)
    if doc.docstatus != 0:
        frappe.throw(_("This run is no longer a draft."))
    if not doc.employees:
        frappe.throw(_("Get the list of people first (step 2)."))
    job = frappe.generate_hash(length=10)
    frappe.cache().set_value(f"reckon_slips:{job}", {"state": "queued", "branches": {}, "total": len(doc.employees)})
    frappe.enqueue("reckon_hrms.api.payroll_run.run_create_slips", queue="long", timeout=3600,
                   job_id=job, name=name, job=job)
    return {"job": job}


def run_create_slips(name, job):
    from hrms.payroll.doctype.payroll_entry.payroll_entry import create_salary_slips_for_employees

    key = f"reckon_slips:{job}"
    doc = frappe.get_doc("Payroll Entry", name)
    people = [r.employee for r in doc.employees]
    office = {r.name: (r.branch or _("No office")) for r in frappe.get_all(
        "Employee", filters={"name": ["in", people]}, fields=["name", "branch"], limit_page_length=0)}
    groups = {}
    for emp in people:
        groups.setdefault(office.get(emp, _("No office")), []).append(emp)
    state = {"state": "running", "branches": {b: {"total": len(e), "done": 0} for b, e in groups.items()},
             "total": len(people)}
    args = _slip_args(doc)
    for branch, emps in groups.items():
        for i in range(0, len(emps), SLIP_BATCH):
            create_salary_slips_for_employees(emps[i:i + SLIP_BATCH], args, publish_progress=False)
            state["branches"][branch]["done"] = min(len(emps), i + SLIP_BATCH)
            frappe.cache().set_value(key, state)
            frappe.publish_realtime("reckon_progress", dict(state, job=job, kind="slips"), user=frappe.session.user)
            frappe.db.commit()
    created = frappe.db.count("Salary Slip", {"payroll_entry": name, "docstatus": 0})
    state.update(state="done", created=created, missing=len(people) - created)
    frappe.cache().set_value(key, state)
    frappe.publish_realtime("reckon_progress", dict(state, job=job, kind="slips"), user=frappe.session.user)


@frappe.whitelist(methods=["GET"])
def get_slip_progress(job: str) -> dict:
    _gate("Payroll Entry", "read")
    return frappe.cache().get_value(f"reckon_slips:{job}") or {"state": "unknown"}


@frappe.whitelist(methods=["GET"])
def review_totals(name: str) -> dict:
    """Step 4: totals over the draft slips, aggregated in SQL, and last month's submitted net for comparison."""
    _gate("Payroll Entry", "read")
    doc = frappe.get_doc("Payroll Entry", name)
    row = frappe.db.sql(
        "SELECT COUNT(name), COALESCE(SUM(gross_pay),0), COALESCE(SUM(total_deduction),0), COALESCE(SUM(net_pay),0) "
        "FROM `tabSalary Slip` WHERE payroll_entry = %(p)s AND docstatus = 0", {"p": name})[0]
    prev_start = get_first_day(add_months(doc.start_date, -1))
    last = frappe.db.sql(
        "SELECT COALESCE(SUM(net_pay),0) FROM `tabSalary Slip` WHERE company = %(c)s AND docstatus = 1 "
        "AND start_date >= %(s)s AND start_date < %(e)s",
        {"c": doc.company, "s": prev_start, "e": doc.start_date})[0][0]
    total_net = flt(row[3])
    change = round(100 * (total_net - flt(last)) / flt(last), 1) if flt(last) else None
    return {"slips": int(row[0]), "gross": flt(row[1]), "deductions": flt(row[2]), "net": total_net,
            "last_month_net": flt(last), "change_percent": change}


@frappe.whitelist(methods=["POST"])
def approve_slips(name: str) -> dict:
    """Step 4: submit every draft slip in background batches."""
    _gate("Payroll Entry", "submit")
    doc = frappe.get_doc("Payroll Entry", name)
    if doc.docstatus != 0:
        frappe.throw(_("This run is no longer a draft."))
    job = frappe.generate_hash(length=10)
    frappe.cache().set_value(f"reckon_submit:{job}", {"state": "queued", "done": 0, "total": 0, "failed": []})
    frappe.enqueue("reckon_hrms.api.payroll_run.run_approve", queue="long", timeout=3600,
                   job_id=job, name=name, job=job)
    return {"job": job}


def run_approve(name, job):
    from hrms.payroll.doctype.payroll_entry.payroll_entry import submit_salary_slips_for_employees

    key = f"reckon_submit:{job}"
    slips = frappe.get_all("Salary Slip", filters={"payroll_entry": name, "docstatus": 0},
                           fields=["name", "employee"], limit_page_length=0)
    state = {"state": "running", "done": 0, "total": len(slips), "failed": []}
    for i in range(0, len(slips), SLIP_BATCH):
        batch = slips[i:i + SLIP_BATCH]
        try:
            submit_salary_slips_for_employees(name, batch, publish_progress=False)
        except Exception as exc:
            state["failed"].append({"batch_start": i, "reason": str(exc)[:160]})
        state["done"] = min(len(slips), i + SLIP_BATCH)
        frappe.cache().set_value(key, state)
        frappe.publish_realtime("reckon_progress", dict(state, job=job, kind="submit"), user=frappe.session.user)
        frappe.db.commit()
    state["state"] = "done"
    frappe.cache().set_value(key, state)
    frappe.publish_realtime("reckon_progress", dict(state, job=job, kind="submit"), user=frappe.session.user)


@frappe.whitelist(methods=["GET"])
def get_submit_progress(job: str) -> dict:
    _gate("Payroll Entry", "read")
    return frappe.cache().get_value(f"reckon_submit:{job}") or {"state": "unknown"}
