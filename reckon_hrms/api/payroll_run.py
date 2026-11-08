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
                                   ["default_currency", "default_payroll_payable_account", "cost_center"], as_dict=True) or {}
    doc = frappe.get_doc({
        "doctype": "Payroll Entry", "company": company, "payroll_frequency": "Monthly",
        "currency": defaults.get("default_currency"), "exchange_rate": 1,
        "payroll_payable_account": defaults.get("default_payroll_payable_account"),
        "cost_center": defaults.get("cost_center"),
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
    missing = missing_pay_item_accounts(name)
    if missing:
        frappe.throw(_("These pay items have no account for this company: {0}. Set an account for each one in Salary rules, then approve again.").format(", ".join(missing)))
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
            submit_salary_slips_for_employees(frappe.get_doc("Payroll Entry", name), [(s.name,) for s in batch], publish_progress=False)
        except Exception as exc:
            state["failed"].append({"batch_start": i, "reason": str(exc)[:160]})
        # HRMS logs per-slip failures instead of raising, so count what actually submitted.
        names = [s.name for s in batch]
        submitted = set(frappe.get_all("Salary Slip", filters={"name": ["in", names], "docstatus": 1}, pluck="name"))
        for s in batch:
            if s.name not in submitted:
                state["failed"].append({"slip": s.name, "employee": s.employee,
                                        "reason": "Not submitted. See the Error Log for the reason."})
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


def missing_pay_item_accounts(name):
    """Pay items on the run's draft slips that have no account for the company (HRMS needs one to post)."""
    company = frappe.db.get_value("Payroll Entry", name, "company")
    rows = frappe.db.sql(
        "SELECT DISTINCT sd.salary_component FROM `tabSalary Detail` sd "
        "JOIN `tabSalary Slip` ss ON sd.parent = ss.name "
        "WHERE ss.payroll_entry = %(p)s AND ss.docstatus = 0 AND sd.parentfield IN ('earnings', 'deductions')",
        {"p": name})
    missing = []
    for (component,) in rows:
        has = bool(frappe.db.get_value("Salary Component Account", {"parent": component, "company": company}, "account"))
        if not has:
            missing.append(component)
    return sorted(missing)


def _is_paid(name) -> bool:
    count = frappe.db.sql("SELECT COUNT(name) FROM `tabSalary Slip` WHERE payroll_entry = %(p)s AND docstatus = 1 AND IFNULL(reckon_payment_entry, '') != ''", {"p": name})[0][0]
    return bool(count)


@frappe.whitelist(methods=["POST"])
def set_payment_hold(name: str, employees: list | str, hold: int = 1, reason: str | None = None) -> dict:
    """Step 5: hold or release payment for submitted slips. Never cancels a slip. Logged as a comment."""
    _gate("Payroll Entry", "write")
    if isinstance(employees, str):
        employees = frappe.parse_json(employees)
    if _is_paid(name):
        frappe.throw(_("This run is already paid. Holds can no longer change."))
    slips = frappe.get_all("Salary Slip", filters={"payroll_entry": name, "docstatus": 1,
                           "employee": ["in", employees or [""]]}, pluck="name")
    for slip in slips:
        frappe.db.set_value("Salary Slip", slip, {"reckon_payment_hold": 1 if hold else 0,
                                                  "reckon_hold_reason": (reason or "") if hold else None})
    doc = frappe.get_doc("Payroll Entry", name)
    doc.add_comment("Comment", "{0} {1} payment for {2} {3} at {4}. Reason: {5}".format(
        frappe.session.user, "held" if hold else "released", len(slips),
        "slip" if len(slips) == 1 else "slips", frappe.utils.now(), reason or "not given"))
    frappe.db.commit()
    return {"changed": len(slips), "hold": bool(hold)}


@frappe.whitelist(methods=["GET"])
def payment_files(name: str, download: int = 0) -> dict:
    """Bank transfer sheet and bKash/Nagad sheet for submitted, non-held slips, plus the hold list.
    Only a real download (download=1) is written to the audit comments."""
    _gate("Payroll Entry", "read")
    if not frappe.has_permission("Salary Slip", "read"):
        frappe.throw(_("You do not have permission to export payment files."), frappe.PermissionError)
    slips = frappe.get_all("Salary Slip", filters={"payroll_entry": name, "docstatus": 1},
                           fields=["employee", "employee_name", "net_pay",
                                   "reckon_payment_hold", "reckon_hold_reason"], order_by="employee asc",
                           limit_page_length=0)
    # Bank and phone details live on the Employee record, not on the slip.
    people = {r.name: r for r in frappe.get_all(
        "Employee", filters={"name": ["in", [s.employee for s in slips] or [""]]},
        fields=["name", "bank_name", "bank_ac_no", "cell_number"], limit_page_length=0)}
    for s in slips:
        person = people.get(s.employee)
        s.bank_name = person.bank_name if person else None
        s.bank_ac_no = person.bank_ac_no if person else None
    cell = {k: v.cell_number for k, v in people.items()}
    bank, wallet, holds = [], [], []
    for s in slips:
        if s.reckon_payment_hold:
            holds.append({"employee": s.employee, "employee_name": s.employee_name, "reason": s.reckon_hold_reason or ""})
        elif s.bank_ac_no:
            bank.append([s.employee, s.employee_name, s.bank_name or "", s.bank_ac_no, f"{flt(s.net_pay):.2f}"])
        elif cell.get(s.employee):
            wallet.append([s.employee, s.employee_name, cell.get(s.employee), f"{flt(s.net_pay):.2f}"])
    if int(download or 0):
        frappe.get_doc("Payroll Entry", name).add_comment("Comment", "{0} downloaded the payment files at {1}.".format(
            frappe.session.user, frappe.utils.now()))
    return {
        "bank_csv": _csv_text(["Employee", "Name", "Bank", "Account", "Net Pay"], bank),
        "wallet_csv": _csv_text(["Employee", "Name", "bKash or Nagad number", "Net Pay"], wallet),
        "bank_count": len(bank), "wallet_count": len(wallet), "hold_count": len(holds), "holds": holds,
        "total_to_pay": round(sum(flt(r[4]) for r in bank) + sum(flt(r[3]) for r in wallet), 2),
    }


def _csv_text(header, rows):
    import csv
    import io

    buf = io.StringIO()
    csv.writer(buf).writerows([header] + rows)
    return buf.getvalue()


@frappe.whitelist(methods=["POST"])
def record_payment(name: str, bank_account: str, reference: str, reference_date: str) -> dict:
    """Step 5: one Journal Entry for the net pay of submitted, non-held slips. Held slips are left out."""
    _gate("Payroll Entry", "submit")
    if not frappe.has_permission("Journal Entry", "create"):
        frappe.throw(_("Only accounts users can record payments."), frappe.PermissionError)
    if _is_paid(name):
        frappe.throw(_("This run is already paid."))
    doc = frappe.get_doc("Payroll Entry", name)
    if doc.docstatus != 1 and not frappe.db.exists("Salary Slip", {"payroll_entry": name, "docstatus": 1}):
        frappe.throw(_("Approve the salary slips before recording payment."))
    if not frappe.db.get_value("Account", {"name": bank_account, "company": doc.company}):
        frappe.throw(_("Choose a bank account of this company."))
    slips = frappe.get_all("Salary Slip", filters={"payroll_entry": name, "docstatus": 1,
                           "reckon_payment_hold": 0}, fields=["name", "net_pay"], limit_page_length=0)
    total = round(sum(flt(s.net_pay) for s in slips), 2)
    if not slips or total <= 0:
        frappe.throw(_("Nothing to pay: every submitted slip is on hold or has no net pay."))
    payable = doc.payroll_payable_account
    if not payable:
        frappe.throw(_("Set the payroll payable account on this run first."))
    je = frappe.get_doc({
        "doctype": "Journal Entry", "voucher_type": "Bank Entry", "company": doc.company,
        "posting_date": getdate(reference_date), "cheque_no": reference, "cheque_date": getdate(reference_date),
        "user_remark": f"Salary payment for {name}",
        "accounts": [
            {"account": payable, "debit_in_account_currency": total},
            {"account": bank_account, "credit_in_account_currency": total},
        ],
    }).insert()
    je.submit()
    for s in slips:
        frappe.db.set_value("Salary Slip", s.name, "reckon_payment_entry", je.name)
    doc.add_comment("Comment", "{0} recorded payment of {1} through {2} at {3}.".format(
        frappe.session.user, total, je.name, frappe.utils.now()))
    frappe.db.commit()
    return {"journal_entry": je.name, "total": total, "slips": len(slips)}
