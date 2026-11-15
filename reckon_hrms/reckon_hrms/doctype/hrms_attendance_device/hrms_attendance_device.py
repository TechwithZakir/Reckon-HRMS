"""A company's ZKTeco / ZKBio Time device: connection settings and the punch sync.

Adapted from "ZKTeco Checkin Sync" by DeliveryDevs-ERP (MIT licence, see docs/THIRD_PARTY.md), made per company.
A device reads punches from its own ZKBio Time server and writes Employee Checkin rows for employees of its
own company only. The scheduler runs this every minute; each device decides for itself whether it is due.
"""

from __future__ import annotations

from datetime import timedelta
from urllib.parse import urljoin, urlparse

import frappe
import requests
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, get_datetime, now_datetime

from reckon_hrms import device_sync as zk

REQUEST_TIMEOUT = 20
OVERLAP = timedelta(minutes=2)  # re-read a little before the last sync; punches already stored are skipped
FIRST_SYNC_WINDOW = timedelta(hours=24)


class HRMSAttendanceDevice(Document):
    def validate(self):
        self.sync_minutes = min(max(int(self.sync_minutes or 5), 1), 60)
        try:
            zk.base_url(self.server_host, self.server_port, self.use_https)
            if self.enabled:
                zk.assert_public_host(self.server_host)
        except ValueError as exc:
            frappe.throw(_(str(exc)))
        changed = not self.is_new() and any(
            self.has_value_changed(f) for f in ("server_host", "server_port", "use_https", "username", "password")
        )
        if changed:
            # a new token is asked for with the new details
            frappe.db.delete("__Auth", {"doctype": self.doctype, "name": self.name, "fieldname": "token"})
            self.auth_scheme = None


# ---- the server ---------------------------------------------------------------------------------------------


def _password(doc, fieldname):
    return doc.get_password(fieldname, raise_exception=False) or ""


def _get(doc, url, **kwargs):
    """GET from the device's server: public hosts only, no redirects (a redirect could lead somewhere internal)."""
    zk.assert_public_host(urlparse(url).hostname or "")
    return requests.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=False, **kwargs)


def register_token(doc) -> str:
    base = zk.base_url(doc.server_host, doc.server_port, doc.use_https)
    zk.assert_public_host(doc.server_host)
    response = requests.post(
        f"{base}/api-token-auth/",
        json={"username": doc.username, "password": _password(doc, "password")},
        timeout=REQUEST_TIMEOUT,
        allow_redirects=False,
    )
    response.raise_for_status()
    token = (response.json() or {}).get("token")
    if not token:
        raise ValueError("The server did not return a token. Check the API username and password.")
    doc.auth_scheme = None
    from frappe.utils.password import set_encrypted_password

    set_encrypted_password("HRMS Attendance Device", doc.name, token, "token")
    return token


def _request_page(doc, url, token, params):
    """One page of transactions. The authorisation scheme the server accepts is found once and kept."""
    schemes = [doc.auth_scheme] if doc.auth_scheme else list(zk.AUTH_SCHEMES)
    response = None
    for scheme in schemes:
        response = _get(doc, url, headers=zk.auth_headers(scheme, token), params=params)
        if response.status_code not in (401, 403):
            if not doc.auth_scheme and response.ok:
                doc.auth_scheme = scheme
                frappe.db.set_value("HRMS Attendance Device", doc.name, "auth_scheme", scheme, update_modified=False)
            return response
    return response


def fetch_transactions(doc, start, end) -> list[dict]:
    """Transactions between two times, following the server's pages (at most ``MAX_PAGES``), same host only."""
    base = zk.base_url(doc.server_host, doc.server_port, doc.use_https)
    token = _password(doc, "token") or register_token(doc)
    url = f"{base}/iclock/api/transactions/"
    params = {
        "start_time": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": end.strftime("%Y-%m-%d %H:%M:%S"),
        "page_size": zk.PAGE_SIZE,
    }
    rows: list[dict] = []
    retried = False
    for _page in range(zk.MAX_PAGES):
        response = _request_page(doc, url, token, params)
        if response.status_code in (401, 403) and not retried:
            retried = True  # the token expired: ask for a new one once
            token = register_token(doc)
            continue
        response.raise_for_status()
        page, next_url = zk.normalise_response(response.json())
        rows.extend(page)
        if not next_url:
            break
        next_url = urljoin(url, next_url)
        if urlparse(next_url).netloc != urlparse(url).netloc:
            break  # the server may only send us to itself
        url, params = next_url, None
    return rows


# ---- employees and check-ins ---------------------------------------------------------------------------------


def find_employee(company: str, code: str) -> str | None:
    """The employee of this company a device code belongs to: device id, then employee id, then user id."""
    lookups = []
    if frappe.db.has_column("Employee", "attendance_device_id"):
        lookups.append({"attendance_device_id": code})
    lookups += [{"name": code}, {"employee_number": code}, {"user_id": code}]
    for extra in lookups:
        if "employee_number" in extra and not frappe.db.has_column("Employee", "employee_number"):
            continue
        name = frappe.db.get_value("Employee", {"company": company, **extra}, "name")
        if name:
            return name
    return None


def store_punch(company: str, parsed: dict) -> str:
    """``created``, ``skipped`` (already stored) or ``unmatched`` (no such employee in this company)."""
    employee = find_employee(company, parsed["code"])
    if not employee:
        return "unmatched"
    if frappe.db.exists("Employee Checkin", {"employee": employee, "time": parsed["time"]}):
        return "skipped"
    frappe.get_doc({
        "doctype": "Employee Checkin",
        "employee": employee,
        "time": parsed["time"],
        "log_type": parsed["log_type"],
        "device_id": zk.checkin_device_label(parsed),
        "skip_auto_attendance": 0,
    }).insert(ignore_permissions=True)
    return "created"


def sync_device(device: str) -> dict:
    """Pull the device's new punches into Employee Checkin. Never raises: the result is kept on the device."""
    doc = frappe.get_doc("HRMS Attendance Device", device)
    if not doc.enabled:
        return {"ok": False, "message": "Disabled"}
    started = now_datetime()
    start = (get_datetime(doc.last_sync) - OVERLAP) if doc.last_sync else started - FIRST_SYNC_WINDOW
    counts = {"created": 0, "skipped": 0, "unmatched": 0, "invalid": 0, "failed": 0}
    unknown: set[str] = set()
    try:
        for row in fetch_transactions(doc, start, started):
            parsed = zk.parse_transaction(row)
            if not parsed:
                counts["invalid"] += 1
                continue
            try:
                outcome = store_punch(doc.company, parsed)
            except Exception:
                counts["failed"] += 1
                frappe.db.rollback()
                continue
            counts[outcome] += 1
            if outcome == "unmatched":
                unknown.add(parsed["code"])
        message = f"{counts['created']} imported, {counts['skipped']} already stored"
        if counts["unmatched"]:
            message += f", {counts['unmatched']} with no employee (codes: {', '.join(sorted(unknown)[:10])})"
        if counts["failed"] or counts["invalid"]:
            message += f", {counts['failed'] + counts['invalid']} could not be read"
        ok = True
    except Exception as exc:
        frappe.db.rollback()
        ok, message = False, f"Failed: {str(exc)[:300]}"
        frappe.log_error(title=f"HRMS device sync {device}")
    values = {"last_status": f"{started:%Y-%m-%d %H:%M}: {message}"}
    if ok:
        values["last_sync"] = started
        values["total_synced"] = int(doc.total_synced or 0) + counts["created"]
    frappe.db.set_value("HRMS Attendance Device", device, values, update_modified=False)
    frappe.db.commit()
    return {"ok": ok, "message": message, **counts}


def run_due_devices() -> None:
    """Scheduler (every minute): queue a sync for each enabled device whose interval has passed."""
    now = now_datetime()
    for row in frappe.get_all("HRMS Attendance Device", filters={"enabled": 1}, fields=["name", "last_sync", "sync_minutes"]):
        try:
            if row.last_sync and add_to_date(get_datetime(row.last_sync), minutes=int(row.sync_minutes or 5)) > now:
                continue
            frappe.enqueue(
                "reckon_hrms.reckon_hrms.doctype.hrms_attendance_device.hrms_attendance_device.sync_device",
                device=row.name, queue="long", job_id=f"hrms_device_{row.name}", deduplicate=True, timeout=300,
            )
        except Exception:
            frappe.log_error(title=f"HRMS device queue {row.name}")


# ---- the buttons on the form ---------------------------------------------------------------------------------


def _own_device(device: str):
    doc = frappe.get_doc("HRMS Attendance Device", device)
    doc.check_permission("write")  # the company's own HR users only (the tenant rules scope this by company)
    return doc


@frappe.whitelist(methods=["POST"])
def test_connection(device: str) -> dict:
    """Ask the server for today's punches and say what came back, without storing anything."""
    doc = _own_device(device)
    try:
        today = now_datetime().replace(hour=0, minute=0, second=0, microsecond=0)
        rows = fetch_transactions(doc, today, now_datetime())
        parsed = [p for p in (zk.parse_transaction(r) for r in rows[:200]) if p]
        known = sum(1 for p in parsed if find_employee(doc.company, p["code"]))
        return {
            "ok": True,
            "message": _("Connected. {0} punches today; {1} of the first {2} match an employee of {3}.").format(
                len(rows), known, len(parsed), doc.company
            ),
        }
    except Exception as exc:
        return {"ok": False, "message": _("Could not connect: {0}").format(str(exc)[:300])}


@frappe.whitelist(methods=["POST"])
def sync_now(device: str) -> dict:
    doc = _own_device(device)
    return sync_device(doc.name)
