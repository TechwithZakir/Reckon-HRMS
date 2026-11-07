"""Operations endpoints: payslip notifications, setup status, statutory estimates, biometric import,
SMS/WhatsApp sending, payroll review and a rule-based assistant.

Provider credentials for SMS/WhatsApp come from site config (hrms_sms_url, hrms_sms_token), never from code.
"""

from __future__ import annotations

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from reckon_hrms import anomaly, bio, messaging, statutory
from reckon_hrms import bd_payroll as bd
from reckon_hrms.api.home import _company
from reckon_hrms.payroll import PRINT_FORMAT

HR_ROLES = ["HR Manager", "Payroll Manager", "System Manager"]


def _require_hr():
    frappe.only_for(HR_ROLES)


def _slips(payroll_entry: str) -> list[dict]:
    if not frappe.has_permission("Payroll Entry", "read", payroll_entry):
        frappe.throw(_("Not permitted to view this payroll run."), frappe.PermissionError)
    return frappe.get_all(
        "Salary Slip", filters={"payroll_entry": payroll_entry, "docstatus": 1},
        fields=["name", "employee", "employee_name", "net_pay", "gross_pay", "bank_ac_no", "start_date",
                "company", "salary_structure"],
        order_by="employee asc", limit_page_length=0,
    )


# ---------- item 4: slip disbursement and notifications ----------

@frappe.whitelist(methods=["POST"])
def send_payslips(payroll_entry: str) -> dict:
    """Email each employee their slip (PDF, bilingual format). Employees without an email are reported."""
    _require_hr()
    sent, missing = 0, []
    for s in _slips(payroll_entry):
        email = frappe.db.get_value("Employee", s.employee, "personal_email") or frappe.db.get_value(
            "Employee", s.employee, "company_email")
        if not email:
            missing.append(s.employee)
            continue
        month = getdate(s.start_date).strftime("%B %Y")
        frappe.sendmail(
            recipients=[email],
            subject=f"Salary slip {month} / {month} বেতন স্লিপ",
            message=messaging.payslip_text(s.employee_name, month, f"{flt(s.net_pay):,.2f}"),
            attachments=[frappe.attach_print("Salary Slip", s.name, print_format=PRINT_FORMAT)],
            reference_doctype="Salary Slip", reference_name=s.name, delayed=False,
        )
        sent += 1
    return {"sent": sent, "missing_email": missing}


# ---------- item 6: setup status ----------

@frappe.whitelist(methods=["GET"])
def setup_status() -> dict:
    """What the setup checklist still needs, in order. Drives the single-page setup on the home page."""
    company = _company()
    steps = [
        ("Departments", frappe.db.exists("Department", {"company": company})),
        ("Holiday calendar", frappe.db.exists("Holiday List", {"company": company})),
        ("Holiday assignment", frappe.db.exists("Holiday List Assignment", {"assigned_to": company, "docstatus": 1})),
        ("Office location", frappe.db.exists("HRMS Office Location", company)),
        ("Leave types", frappe.db.count("Leave Type") > 0),
        ("Salary components", frappe.db.exists("Salary Component", "Basic Salary")),
        ("Bangladesh payroll structure", frappe.db.exists("Salary Structure", f"Reckon BD SME - {company}")),
        ("Payslip format", frappe.db.exists("Print Format", "Reckon Payslip (Bilingual)")),
    ]
    rows = [{"label": label, "done": bool(done)} for label, done in steps]
    next_step = next((r["label"] for r in rows if not r["done"]), None)
    return {"company": company, "steps": rows, "done": sum(r["done"] for r in rows), "total": len(rows),
            "next": next_step}


# ---------- item 7: statutory estimates ----------

@frappe.whitelist(methods=["GET"])
def gratuity_estimate(employee: str, last_basic: float) -> dict:
    if not frappe.has_permission("Employee", "read", employee):
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    joined = frappe.db.get_value("Employee", employee, "date_of_joining")
    if not joined:
        frappe.throw(_("Employee has no joining date."))
    years = (getdate(nowdate()) - getdate(joined)).days / 365.25
    return {"employee": employee, "years": round(years, 2), "gratuity": float(statutory.gratuity(last_basic, years))}


@frappe.whitelist(methods=["GET"])
def wppf_estimate(gross_profit: float) -> dict:
    _require_hr()
    company = _company()
    workers = frappe.db.count("Employee", {"company": company, "status": "Active"})
    return {"company": company, "workers": workers,
            "wppf": float(statutory.wppf_contribution(flt(gross_profit), workers))}


# ---------- item 8: biometric import ----------

@frappe.whitelist(methods=["POST"])
def import_biometric(csv_text: str) -> dict:
    """Import a terminal export. Codes match Employee.attendance_device_id. Existing punches are skipped."""
    _require_hr()
    punches, errors = bio.parse_punches(csv_text)
    punches = bio.infer_directions(punches)
    created, duplicates, unknown = 0, 0, set()
    for p in punches:
        employee = frappe.db.get_value("Employee", {"attendance_device_id": p["employee_code"]}, "name")
        if not employee:
            unknown.add(p["employee_code"])
            continue
        exists = frappe.db.exists("Employee Checkin", {"employee": employee, "time": p["time"], "log_type": p["log_type"]})
        if exists:
            duplicates += 1
            continue
        frappe.get_doc({"doctype": "Employee Checkin", "employee": employee, "log_type": p["log_type"],
                        "time": p["time"], "device_id": p["employee_code"], "skip_auto_attendance": 1}
                       ).insert(ignore_permissions=True)
        created += 1
    frappe.db.commit()
    return {"created": created, "duplicates": duplicates, "unknown_codes": sorted(unknown), "errors": errors}


# ---------- item 9: SMS and WhatsApp ----------

def _adapter():
    url = frappe.conf.get("hrms_sms_url")
    token = frappe.conf.get("hrms_sms_token")

    def post(url_, payload, headers):
        import requests

        return requests.post(url_, json=payload, headers=headers, timeout=15).status_code

    return messaging.WebhookAdapter(url, token, post)


@frappe.whitelist(methods=["POST"])
def send_payslip_sms(payroll_entry: str, channel: str = "sms") -> dict:
    _require_hr()
    if channel not in ("sms", "whatsapp"):
        frappe.throw(_("Choose sms or whatsapp."))
    messages = []
    for s in _slips(payroll_entry):
        phone = frappe.db.get_value("Employee", s.employee, "cell_number")
        if not phone:
            continue
        month = getdate(s.start_date).strftime("%B %Y")
        messages.append(messaging.Message(phone, messaging.payslip_text(s.employee_name, month,
                                          f"{flt(s.net_pay):,.2f}"), channel))
    result = messaging.dispatch(messages, _adapter())
    return {"sent": result.sent, "skipped": result.skipped, "failed": result.failed}


# ---------- item 10: anomaly review and assistant ----------

@frappe.whitelist(methods=["GET"])
def payroll_review(payroll_entry: str) -> list[dict]:
    _require_hr()
    slips = _slips(payroll_entry)
    rows = []
    for s in slips:
        full = frappe.get_doc("Salary Slip", s.name)
        tds = sum(flt(r.amount) for r in full.deductions if r.abbr == "TDS")
        pf = sum(flt(r.amount) for r in full.deductions if r.abbr == "PFEMP")
        expected = float(bd.monthly_tds(flt(full.gross_pay), pf))
        prev = frappe.get_all("Salary Slip", filters={"employee": s.employee, "docstatus": 1,
                              "start_date": ["<", full.start_date]}, fields=["net_pay"],
                              order_by="start_date desc", limit=1)
        attendance = frappe.db.count("Attendance", {"employee": s.employee, "status": ["in", ["Present", "Work From Home", "Half Day"]],
                                                    "attendance_date": ["between", [full.start_date, full.end_date]]})
        rows.append({"employee": s.employee, "net_pay": flt(full.net_pay), "previous_net": flt(prev[0].net_pay) if prev else None,
                     "tds": tds, "expected_tds": expected, "bank_ac_no": s.bank_ac_no or "",
                     "present_days": attendance, "working_days": full.total_working_days or 0})
    return anomaly.review(rows)


@frappe.whitelist(methods=["GET"])
def assistant(question: str) -> dict:
    """Rule-based helper over the same numbers the home page shows. It answers only what it can compute."""
    from reckon_hrms.api.home import get_home

    q = (question or "").lower()
    data = get_home()
    kpis = {k["label"].lower(): k["value"] for k in data.get("kpis", [])}
    if "absent" in q or "present" in q or "attendance" in q:
        return {"answer": f"Attendance rate over 30 days: {kpis.get('attendance rate (30 days)', 'n/a')}. "
                          f"Present today: {kpis.get('present today', 'n/a')}."}
    if "leave" in q:
        return {"answer": f"Pending leave requests: {kpis.get('pending leave requests', 'n/a')}."}
    if "payroll" in q or "salary" in q or "pay" in q:
        return {"answer": f"Draft payroll runs: {kpis.get('draft payroll runs', 'n/a')}."}
    if "todo" in q or "pending" in q or "do" in q:
        todos = [t["label"] for t in data.get("todos", [])]
        return {"answer": "; ".join(todos) if todos else "Nothing waiting for you."}
    return {"answer": "I can answer about attendance, leave, payroll and your to-do list. Try one of those."}
