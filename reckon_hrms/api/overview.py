"""The Home page: a plain overview in the same shape as the Accounts home.

Numbers, a get-started checklist, quick actions, recent items and report links. Everything is scoped to the
caller's company; an employee with only self-service sees the quick actions and no company numbers.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, get_first_day, getdate, nowdate

from reckon_hrms.api.home import (
    PRESENT,
    REPORTS,
    _company,
    _manager_onboarding,
    home_view,
)


def _count(doctype: str, filters: dict) -> int:
    return len(frappe.get_all(doctype, filters=filters, pluck="name", limit_page_length=0))


@frappe.whitelist(methods=["GET"])
def get_overview() -> dict:
    view = home_view(frappe.get_roles())
    today = getdate(nowdate())
    base = {"view": view, "today": str(today), "reports": REPORTS}
    if view == "self":
        return {**base, "company": "", "kpis": [], "checklist": [], "recent_leaves": [], "recent_joiners": []}

    company = _company()
    employees = frappe.get_all(
        "Employee", filters={"company": company, "status": "Active"}, fields=["name", "employee_name", "date_of_joining"],
        order_by="date_of_joining desc", limit_page_length=0,
    )
    marked = frappe.get_all(
        "Attendance", filters={"company": company, "attendance_date": today, "docstatus": ["!=", 2]},
        fields=["status"], limit_page_length=0,
    )
    month_start = get_first_day(today)
    kpis = [
        {"label": _("Employees"), "value": len(employees), "route": "/app/employee", "tone": ""},
        {"label": _("Present today"), "value": sum(1 for a in marked if a.status in PRESENT), "route": "/app/attendance", "tone": "is-green"},
        {"label": _("On leave today"), "value": sum(1 for a in marked if a.status == "On Leave"), "route": "/app/leave-application", "tone": "is-blue"},
        {"label": _("Leave waiting for approval"), "value": _count("Leave Application", {"company": company, "status": "Open", "docstatus": 0}),
         "route": "/app/leave-application?status=Open", "tone": "is-amber"},
        {"label": _("Joined this month"), "value": sum(1 for e in employees if e.date_of_joining and getdate(e.date_of_joining) >= month_start),
         "route": "/app/employee", "tone": ""},
        {"label": _("Salary slips this month"), "value": _count("Salary Slip", {"company": company, "start_date": [">=", month_start], "docstatus": ["!=", 2]}),
         "route": "/app/salary-slip", "tone": ""},
    ]
    return {
        **base,
        "company": company,
        "kpis": kpis,
        "checklist": _manager_onboarding(company, len(employees)),
        "recent_leaves": frappe.get_all(
            "Leave Application", filters={"company": company, "docstatus": ["!=", 2]},
            fields=["name", "employee_name", "leave_type", "from_date", "to_date", "status"], order_by="creation desc", limit_page_length=6,
        ),
        "recent_joiners": [{"name": e.name, "employee_name": e.employee_name, "date_of_joining": str(e.date_of_joining or "")} for e in employees[:6]],
        "since": str(add_days(today, -30)),
    }
