"""End-to-end attendance test on the demo HRMS alpha company (run server-side as each user).

Sets the office location, checks in inside and outside the fence, checks out, marks bulk attendance,
then removes its own test records.
"""

import sys
import frappe

frappe.init(site=sys.argv[1])
frappe.connect()
from reckon_hrms.api import attendance as att

COMPANY = "RD Demo HRMS Alpha Ltd"
ADMIN = "demo.hrms.alpha@example.com"
ESS = "demo.ess.attend@example.com"
OFFICE = (23.8103, 90.4125)

if not frappe.db.exists("HRMS Office Location", COMPANY):
    frappe.get_doc({"doctype": "HRMS Office Location", "company": COMPANY, "latitude": OFFICE[0],
                    "longitude": OFFICE[1], "radius_m": 150}).insert(ignore_permissions=True)
frappe.db.commit()

if not frappe.db.exists("User", ESS):
    frappe.get_doc({"doctype": "User", "email": ESS, "first_name": "Attend Test", "enabled": 1,
                    "send_welcome_email": 0}).insert(ignore_permissions=True)
emp = frappe.db.get_value("Employee", {"user_id": ESS}, "name")
if not emp:
    emp = frappe.get_doc({"doctype": "Employee", "first_name": "Attend", "last_name": "Test", "gender": "Male",
                          "date_of_birth": "1997-05-05", "date_of_joining": "2025-03-01", "status": "Active",
                          "company": COMPANY, "user_id": ESS}).insert(ignore_permissions=True).name
frappe.db.commit()


def as_user(user, fn, *args, **kwargs):
    frappe.set_user(user)
    try:
        return fn(*args, **kwargs)
    finally:
        frappe.set_user("Administrator")


def attempt(label, fn, *args, **kwargs):
    try:
        out = as_user(ESS, fn, *args, **kwargs)
        print("RESULT", label, "OK", out.get("log_type", ""), out.get("distance_m", ""))
    except frappe.exceptions.ValidationError as exc:
        print("RESULT", label, "REFUSED", str(exc)[:90])
    except frappe.PermissionError as exc:
        print("RESULT", label, "DENIED", str(exc)[:90])


attempt("inside_checkin", att.punch, "IN", OFFICE[0] + 0.0002, OFFICE[1] + 0.0002)
attempt("duplicate_checkin", att.punch, "IN", OFFICE[0], OFFICE[1])
attempt("far_checkout", att.punch, "OUT", OFFICE[0] + 0.01, OFFICE[1])
attempt("inside_checkout", att.punch, "OUT", OFFICE[0], OFFICE[1])
print("STATUS_AFTER", as_user(ESS, att.my_status)["checked_in"])

result = as_user(ADMIN, att.bulk_mark, None, "Present", [emp])
print("BULK", result)
print("BULK_AGAIN", as_user(ADMIN, att.bulk_mark, None, "Present", [emp]))

rows = frappe.get_all("Attendance", filters={"employee": emp}, fields=["attendance_date", "status", "working_hours"])
print("ATTENDANCE_ROWS", len(rows))
print("CHECKINS", frappe.get_all("Employee Checkin", filters={"employee": emp}, fields=["log_type", "time"], order_by="time desc"))

frappe.db.delete("Attendance", {"employee": emp})
frappe.db.delete("Employee Checkin", {"employee": emp})
frappe.delete_doc("Employee", emp, ignore_permissions=True, force=True)
frappe.delete_doc("User", ESS, ignore_permissions=True, force=True)
frappe.db.commit()
print("CLEANED")
