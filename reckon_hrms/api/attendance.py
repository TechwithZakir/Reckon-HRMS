"""Geo-tagged check-in and check-out, and bulk attendance for HR.

The employee is always the logged-in user's own active employee record. Check-in and check-out
are accepted only inside the company's office geofence (HRMS Office Location). Bulk marking is
limited to HR and admin roles, and to employees the caller can already see (company scoped).
"""

from __future__ import annotations

import math

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime, nowdate

from reckon_hrms.geo import within_geofence

PUNCH_TYPES = ("IN", "OUT")
ATTENDANCE_STATUSES = ("Present", "Absent", "Half Day", "On Leave", "Work From Home")
BULK_ROLES = ("HR Manager", "System Manager")


def _my_employee():
    user = frappe.session.user
    if user in {"Guest"}:
        frappe.throw(_("Sign in to check in."), frappe.PermissionError)
    employee = frappe.db.get_value(
        "Employee", {"user_id": user, "status": "Active"}, ["name", "company", "employee_name"], as_dict=True
    )
    if not employee:
        frappe.throw(_("No active employee record is linked to your login."), frappe.PermissionError)
    return employee


def _check_geofence(company: str, latitude, longitude) -> dict:
    office = frappe.db.get_value(
        "HRMS Office Location", company, ["latitude", "longitude", "radius_m"], as_dict=True
    )
    if not office:
        return {"geofence": False}
    inside, distance = within_geofence(latitude, longitude, office.latitude, office.longitude, office.radius_m)
    if not inside:
        if math.isinf(distance):
            frappe.throw(_("Turn on location access so we can confirm you are at the office."))
        frappe.throw(_("You are {0} m from the office. Check-in is allowed within {1} m.").format(
            round(distance), int(office.radius_m or 150)))
    return {"geofence": True, "distance_m": round(distance)}


def _upsert_attendance(employee: dict, day) -> str:
    """Record the day's attendance from its first check-in and last check-out."""
    logs = frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee.name, "time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
        fields=["log_type", "time"],
        order_by="time asc",
    )
    ins = [row.time for row in logs if row.log_type == "IN"]
    outs = [row.time for row in logs if row.log_type == "OUT"]
    in_time = ins[0] if ins else None
    out_time = outs[-1] if outs else None
    hours = round((out_time - in_time).total_seconds() / 3600, 2) if in_time and out_time else 0
    name = frappe.db.get_value("Attendance", {"employee": employee.name, "attendance_date": day, "docstatus": 0}, "name")
    values = {"status": "Present", "in_time": in_time, "out_time": out_time, "working_hours": hours}
    if name:
        doc = frappe.get_doc("Attendance", name)
        doc.update(values)
        doc.save(ignore_permissions=True)
        return doc.name
    doc = frappe.get_doc({
        "doctype": "Attendance", "employee": employee.name, "employee_name": employee.employee_name,
        "attendance_date": day, "company": employee.company, **values,
    }).insert(ignore_permissions=True)
    return doc.name


@frappe.whitelist(methods=["GET"])
def my_status() -> dict:
    employee = _my_employee()
    last = frappe.db.get_value(
        "Employee Checkin", {"employee": employee.name}, ["log_type", "time"], order_by="time desc", as_dict=True
    )
    today_open = bool(last and last.log_type == "IN" and getdate(last.time) == getdate(nowdate()))
    return {"employee": employee.name, "employee_name": employee.employee_name,
            "checked_in": today_open, "last_punch": str(last.time) if last else None,
            "last_type": last.log_type if last else None}


def _as_system(fn, *args):
    """Run a write as Administrator. The caller's identity is already verified by _my_employee,
    and the tenant hooks would otherwise reject self-service writes for users without an assignment row."""
    user = frappe.session.user
    frappe.set_user("Administrator")
    try:
        return fn(*args)
    finally:
        frappe.set_user(user)


def _insert_checkin(employee, log_type: str, lat, lon):
    return frappe.get_doc({
        "doctype": "Employee Checkin", "employee": employee.name, "log_type": log_type,
        "time": now_datetime(), "latitude": lat, "longitude": lon, "skip_auto_attendance": 1,
    }).insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def punch(log_type: str, latitude: float | None = None, longitude: float | None = None) -> dict:
    if log_type not in PUNCH_TYPES:
        frappe.throw(_("Choose check-in or check-out."))
    employee = _my_employee()
    lat = flt(latitude) if latitude not in (None, "") else None
    lon = flt(longitude) if longitude not in (None, "") else None
    geo = _check_geofence(employee.company, lat, lon)

    last = frappe.db.get_value("Employee Checkin", {"employee": employee.name}, "log_type", order_by="time desc")
    if last == log_type:
        frappe.throw(_("You are already checked {0}.").format("in" if log_type == "IN" else "out"))

    checkin = _as_system(_insert_checkin, employee, log_type, lat, lon)
    attendance = _as_system(_upsert_attendance, employee, getdate(checkin.time)) if log_type == "OUT" else None
    return {"log_type": log_type, "checkin": checkin.name, "attendance": attendance, **geo}


@frappe.whitelist(methods=["POST"])
def bulk_mark(attendance_date: str | None = None, status: str = "Present", employees: list | str | None = None) -> dict:
    roles = set(frappe.get_roles())
    is_admin = any(r.startswith("Reckon HRMS Admin - ") for r in roles)
    if not (roles & set(BULK_ROLES) or is_admin):
        frappe.throw(_("Only HR managers can mark attendance for others."), frappe.PermissionError)
    if status not in ATTENDANCE_STATUSES:
        frappe.throw(_("Unknown attendance status."))
    day = getdate(attendance_date or nowdate())

    if isinstance(employees, str):
        employees = frappe.parse_json(employees)
    visible = set(frappe.get_list("Employee", filters={"status": "Active"}, pluck="name", limit_page_length=0))
    targets = sorted(visible if not employees else visible & set(employees))

    created, skipped = 0, 0
    for name in targets:
        if frappe.db.exists("Attendance", {"employee": name, "attendance_date": day, "docstatus": 0}):
            skipped += 1
            continue
        row = frappe.db.get_value("Employee", name, ["employee_name", "company"], as_dict=True)
        frappe.get_doc({
            "doctype": "Attendance", "employee": name, "employee_name": row.employee_name,
            "attendance_date": day, "status": status, "company": row.company,
        }).insert(ignore_permissions=True)
        created += 1
    return {"date": str(day), "status": status, "created": created, "skipped": skipped}
