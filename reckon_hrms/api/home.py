"""Role-specific home data: onboarding, to-dos, pending items, suggestions, KPIs and reports.

Three views, chosen from the caller's roles:
  manager  - HR Manager, System Manager, or a tenant "Reckon HRMS Admin - <Company>"
  payroll  - Payroll Manager
  self     - everyone else who has an employee record (Employee Self Service)

Manager and payroll counts are scoped explicitly to one company, so they never mix tenants.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, flt, get_first_day, getdate, nowdate

from reckon_hrms.api.attendance import _my_employee

PRESENT = ("Present", "Work From Home", "Half Day")
REPORTS = [
    {"label": "Monthly attendance sheet", "route": "/app/query-report/Monthly Attendance Sheet"},
    {"label": "Attendance", "route": "/app/attendance"},
    {"label": "Leave applications", "route": "/app/leave-application"},
    {"label": "Employee leave balance", "route": "/app/query-report/Employee Leave Balance"},
    {"label": "Payroll entries", "route": "/app/payroll-entry"},
    {"label": "Salary register", "route": "/app/query-report/Salary Register"},
    {"label": "Employees", "route": "/app/employee"},
]
PROFILE_FIELDS = ("date_of_birth", "cell_number", "personal_email", "emergency_phone_number", "bank_ac_no")


def home_view(roles) -> str:
    roles = set(roles)
    if any(r.startswith("Reckon HRMS Admin - ") for r in roles) or roles & {"HR Manager", "System Manager"}:
        return "manager"
    if "Payroll Manager" in roles:
        return "payroll"
    return "self"


def _company() -> str:
    default = frappe.defaults.get_user_default("Company")
    if default:
        return default
    companies = frappe.get_list("Company", pluck="name", limit_page_length=1)
    if not companies:
        frappe.throw(_("No company is assigned to your login."), frappe.PermissionError)
    return companies[0]


def _item(label, value, route=None, tone="neutral"):
    return {"label": label, "value": value, "route": route, "tone": tone}


def _pct(part, whole):
    return round(100 * part / whole, 1) if whole else None


# ---------- manager ----------

def _manager(company: str) -> dict:
    today = getdate(nowdate())
    month_start = get_first_day(today)
    window_start = add_days(today, -30)

    employees = frappe.get_all(
        "Employee", filters={"company": company, "status": "Active"},
        fields=["name", "employee_name", "department", "date_of_joining"], limit_page_length=0,
    )
    headcount = len(employees)
    marked_today = frappe.get_all(
        "Attendance", filters={"company": company, "attendance_date": today, "docstatus": ["!=", 2]},
        fields=["employee", "status"], limit_page_length=0,
    )
    present_today = sum(1 for a in marked_today if a.status in PRESENT)
    on_leave_today = sum(1 for a in marked_today if a.status == "On Leave")
    marked_names = {a.employee for a in marked_today}
    missing = [e for e in employees if e.name not in marked_names]

    pending_leaves = frappe.get_all(
        "Leave Application", filters={"company": company, "status": "Open", "docstatus": ["!=", 2]},
        fields=["name", "employee_name", "leave_type", "from_date", "to_date"],
        order_by="creation asc", limit_page_length=0,
    )
    draft_payrolls = frappe.get_all(
        "Payroll Entry", filters={"company": company, "docstatus": 0},
        fields=["name", "posting_date", "start_date", "end_date"], limit_page_length=0,
    )

    window_rows = frappe.get_all(
        "Attendance", filters={"company": company, "attendance_date": ["between", [window_start, today]],
                               "docstatus": ["!=", 2]},
        fields=["employee", "status"], limit_page_length=0,
    )
    window_present = sum(1 for r in window_rows if r.status in PRESENT)
    attendance_rate = _pct(window_present, len(window_rows))

    approved_leave_days_month = sum(
        flt(r.total_leave_days) for r in frappe.get_all(
            "Leave Application", filters={"company": company, "status": "Approved", "docstatus": 1,
                                          "from_date": [">=", month_start]},
            fields=["total_leave_days"], limit_page_length=0)
    )
    joiners_month = sum(1 for e in employees if e.date_of_joining and getdate(e.date_of_joining) >= month_start)

    # Per-employee 30-day KPI table: present days, leave days, absent days.
    per_emp = {e.name: {"employee": e.name, "employee_name": e.employee_name, "department": e.department,
                        "present": 0, "leave": 0, "absent": 0} for e in employees}
    for r in window_rows:
        row = per_emp.get(r.employee)
        if not row:
            continue
        if r.status in PRESENT:
            row["present"] += 1
        elif r.status == "On Leave":
            row["leave"] += 1
        elif r.status == "Absent":
            row["absent"] += 1
    employee_kpis = sorted(per_emp.values(), key=lambda x: (-x["absent"], x["employee_name"] or ""))[:25]

    # Department breakdown.
    dept = {}
    for e in employees:
        key = e.department or _("Unassigned")
        dept.setdefault(key, {"department": key, "headcount": 0, "present_today": 0})
        dept[key]["headcount"] += 1
    emp_dept = {e.name: (e.department or _("Unassigned")) for e in employees}
    for a in marked_today:
        if a.status in PRESENT and a.employee in emp_dept:
            dept[emp_dept[a.employee]]["present_today"] += 1
    departments = sorted(dept.values(), key=lambda x: -x["headcount"])

    onboarding = _manager_onboarding(company, headcount)
    onboarding_done = sum(1 for s in onboarding if s["done"])

    todos = []
    if pending_leaves:
        todos.append(_item(_("Leave requests waiting for approval"), len(pending_leaves), "/app/leave-application?status=Open", "warn"))
    if missing:
        todos.append(_item(_("Employees without attendance today"), len(missing), "/app/attendance", "warn"))
    if draft_payrolls:
        todos.append(_item(_("Draft payroll runs to submit"), len(draft_payrolls), "/app/payroll-entry", "warn"))
    if onboarding_done < len(onboarding):
        todos.append(_item(_("Finish setup checklist"), f"{onboarding_done}/{len(onboarding)}", None, "info"))

    pending = [
        {"type": _("Leave"), "title": f"{p.employee_name} · {p.leave_type}",
         "detail": f"{p.from_date} → {p.to_date}", "route": f"/app/leave-application/{p.name}"}
        for p in pending_leaves[:10]
    ] + [
        {"type": _("Payroll"), "title": p.name, "detail": f"{p.start_date} → {p.end_date}",
         "route": f"/app/payroll-entry/{p.name}"}
        for p in draft_payrolls[:5]
    ]

    suggestions = []
    if not onboarding_done == len(onboarding):
        suggestions.append(_("Complete the setup checklist to unlock attendance, leave and payroll."))
    if missing:
        suggestions.append(_("Use bulk marking to record today's attendance for the {0} employees left.").format(len(missing)))
    if attendance_rate is not None and attendance_rate < 85:
        suggestions.append(_("Attendance is {0}% over the last 30 days. Review absences by department.").format(attendance_rate))
    if pending_leaves:
        suggestions.append(_("Approve or reject the {0} open leave requests so employees can plan.").format(len(pending_leaves)))
    if not frappe.db.exists("HRMS Office Location", company):
        suggestions.append(_("Set the office location so check-in can use the geofence."))

    kpis = [
        _item(_("Headcount"), headcount, "/app/employee"),
        _item(_("Present today"), present_today, "/app/attendance"),
        _item(_("On leave today"), on_leave_today, "/app/leave-application"),
        _item(_("Pending leave requests"), len(pending_leaves), "/app/leave-application?status=Open",
              "warn" if pending_leaves else "neutral"),
        _item(_("Attendance rate (30 days)"), f"{attendance_rate}%" if attendance_rate is not None else "—"),
        _item(_("New joiners this month"), joiners_month),
        _item(_("Approved leave days this month"), approved_leave_days_month),
        _item(_("Draft payroll runs"), len(draft_payrolls), "/app/payroll-entry"),
    ]
    return {
        "view": "manager", "company": company, "greeting_date": str(today),
        "onboarding": {"steps": onboarding, "done": onboarding_done, "total": len(onboarding)},
        "todos": todos, "pending": pending, "suggestions": suggestions,
        "kpis": kpis,
        "detailed": {"departments": departments, "employees": employee_kpis,
                     "window_days": 30, "window_rows": len(window_rows)},
        "reports": REPORTS,
    }


def _manager_onboarding(company: str, headcount: int) -> list[dict]:
    def has(doctype, filters):
        return bool(frappe.get_list(doctype, filters=filters, pluck="name", limit_page_length=1))

    return [
        {"label": _("Departments"), "done": has("Department", {"company": company}), "route": "/app/department/new"},
        {"label": _("Holiday calendar"), "done": has("Holiday List", {"company": company}), "route": "/app/holiday-list/new"},
        {"label": _("Office location for check-in"), "done": bool(frappe.db.exists("HRMS Office Location", company)),
         "route": "/app/hrms-office-location/new"},
        {"label": _("Leave types"), "done": has("Leave Type", {}), "route": "/app/leave-type/new"},
        {"label": _("Shift type"), "done": has("Shift Type", {}), "route": "/app/shift-type/new"},
        {"label": _("First employee"), "done": headcount > 0, "route": "/app/employee/new"},
        {"label": _("Salary components"), "done": has("Salary Component", {}), "route": "/app/salary-component/new"},
        {"label": _("Salary structure"), "done": has("Salary Structure", {"company": company}), "route": "/app/salary-structure/new"},
    ]


# ---------- payroll ----------

def _payroll(company: str) -> dict:
    today = getdate(nowdate())
    month_start = get_first_day(today)
    employees = frappe.get_all("Employee", filters={"company": company, "status": "Active"},
                               pluck="name", limit_page_length=0)
    assigned = set(frappe.get_all(
        "Salary Structure Assignment", filters={"company": company, "docstatus": 1},
        pluck="employee", limit_page_length=0))
    unassigned = [e for e in employees if e not in assigned]
    drafts = frappe.get_all("Payroll Entry", filters={"company": company, "docstatus": 0},
                            fields=["name", "start_date", "end_date"], limit_page_length=0)
    slips = frappe.get_all(
        "Salary Slip", filters={"company": company, "docstatus": 1, "posting_date": [">=", month_start]},
        fields=["net_pay"], limit_page_length=0)
    net_month = sum(flt(s.net_pay) for s in slips)

    todos = []
    if drafts:
        todos.append(_item(_("Payroll runs to submit"), len(drafts), "/app/payroll-entry", "warn"))
    if unassigned:
        todos.append(_item(_("Employees without a salary structure"), len(unassigned),
                           "/app/salary-structure-assignment", "warn"))

    suggestions = []
    if unassigned:
        suggestions.append(_("Assign a salary structure to the {0} employees who have none.").format(len(unassigned)))
    if not drafts and not slips:
        suggestions.append(_("Create this month's payroll run once attendance is complete."))

    return {
        "view": "payroll", "company": company, "greeting_date": str(today),
        "onboarding": {"steps": [], "done": 0, "total": 0},
        "todos": todos,
        "pending": [{"type": _("Payroll"), "title": d.name, "detail": f"{d.start_date} → {d.end_date}",
                     "route": f"/app/payroll-entry/{d.name}"} for d in drafts[:10]],
        "suggestions": suggestions,
        "kpis": [
            _item(_("Active employees"), len(employees), "/app/employee"),
            _item(_("With salary structure"), len(assigned & set(employees)), "/app/salary-structure-assignment"),
            _item(_("Without salary structure"), len(unassigned), "/app/salary-structure-assignment",
                  "warn" if unassigned else "neutral"),
            _item(_("Draft payroll runs"), len(drafts), "/app/payroll-entry", "warn" if drafts else "neutral"),
            _item(_("Salary slips this month"), len(slips), "/app/salary-slip"),
            _item(_("Net pay this month"), f"{net_month:,.0f}"),
        ],
        "detailed": {"unassigned_employees": unassigned[:25]},
        "reports": [r for r in REPORTS if "payroll" in r["route"] or "salary" in r["route"] or "attendance" in r["route"].lower()],
    }


# ---------- self ----------

def _self(employee) -> dict:
    today = getdate(nowdate())
    month_start = get_first_day(today)
    window_start = add_days(today, -30)
    rows = frappe.get_all("Attendance", filters={"employee": employee.name,
                          "attendance_date": ["between", [window_start, today]], "docstatus": ["!=", 2]},
                          fields=["status"], limit_page_length=0)
    present = sum(1 for r in rows if r.status in PRESENT)
    last = frappe.db.get_value("Employee Checkin", {"employee": employee.name}, ["log_type", "time"],
                               order_by="time desc, creation desc", as_dict=True)
    checked_in = bool(last and last.log_type == "IN" and getdate(last.time) == today)
    my_leaves = frappe.get_all("Leave Application", filters={"employee": employee.name,
                               "from_date": [">=", month_start]},
                               fields=["name", "leave_type", "from_date", "to_date", "status"], limit_page_length=0)
    pending_mine = [l for l in my_leaves if l.status == "Open"]

    holiday_list = frappe.db.get_value("Employee", employee.name, "holiday_list") or frappe.db.get_value(
        "Holiday List", {"company": employee.company}, "name")
    upcoming = []
    if holiday_list:
        upcoming = frappe.get_all("Holiday", filters={"parent": holiday_list,
                                  "holiday_date": [">=", today]},
                                  fields=["holiday_date", "description"], order_by="holiday_date asc", limit=3)

    profile = frappe.db.get_value("Employee", employee.name, list(PROFILE_FIELDS), as_dict=True) or {}
    missing_profile = [f for f in PROFILE_FIELDS if not profile.get(f)]

    onboarding = [
        {"label": _("Complete your profile"), "done": not missing_profile, "route": f"/app/employee/{employee.name}"},
        {"label": _("Check in for today"), "done": checked_in, "route": "/hrms-checkin"},
        {"label": _("Read the holiday calendar"), "done": bool(holiday_list), "route": "/app/holiday-list"},
    ]
    todos = []
    if not checked_in:
        todos.append(_item(_("Check in for today"), _("Not yet"), "/hrms-checkin", "warn"))
    if missing_profile:
        todos.append(_item(_("Fill in your profile details"), len(missing_profile), f"/app/employee/{employee.name}", "info"))
    if pending_mine:
        todos.append(_item(_("Your leave requests waiting for approval"), len(pending_mine), "/app/leave-application", "info"))

    suggestions = []
    if rows and _pct(present, len(rows)) is not None and _pct(present, len(rows)) < 90:
        suggestions.append(_("Your attendance is {0}% over the last 30 days.").format(_pct(present, len(rows))))
    if missing_profile:
        suggestions.append(_("Add {0} to your profile so payroll and records stay accurate.").format(", ".join(missing_profile)))
    if not suggestions:
        suggestions.append(_("You are all caught up. Enjoy your day."))

    return {
        "view": "self", "company": employee.company, "greeting_date": str(today),
        "employee_name": employee.employee_name,
        "onboarding": {"steps": onboarding, "done": sum(1 for s in onboarding if s["done"]), "total": len(onboarding)},
        "todos": todos,
        "pending": [{"type": _("Leave"), "title": f"{l.leave_type}", "detail": f"{l.from_date} → {l.to_date} · {l.status}",
                     "route": f"/app/leave-application/{l.name}"} for l in my_leaves[:10]],
        "suggestions": suggestions,
        "kpis": [
            _item(_("Checked in today"), _("Yes") if checked_in else _("No"), None, "good" if checked_in else "warn"),
            _item(_("Attendance (30 days)"), f"{_pct(present, len(rows))}%" if rows else "—"),
            _item(_("Days present (30 days)"), present),
            _item(_("Leave requests this month"), len(my_leaves)),
        ],
        "detailed": {"upcoming_holidays": [{"date": str(h.holiday_date), "name": h.description} for h in upcoming]},
        "reports": [{"label": _("My attendance"), "route": "/app/attendance"},
                    {"label": _("My leave applications"), "route": "/app/leave-application"},
                    {"label": _("My check-in"), "route": "/hrms-checkin"}],
    }


@frappe.whitelist(methods=["GET"])
def get_home() -> dict:
    roles = frappe.get_roles()
    view = home_view(roles)
    if view == "self":
        return _self(_my_employee())
    company = _company()
    return _manager(company) if view == "manager" else _payroll(company)
