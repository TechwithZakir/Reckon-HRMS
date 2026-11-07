"""HTTP-level desk guard and isolation test for the demo tenants.

Creates a server-side session for each demo user (no password is typed into the
site), sends real requests through the local web server with that session cookie,
then deletes the sessions.
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

import frappe
from frappe.auth import LoginManager

SITE = sys.argv[1]
BASE = "http://127.0.0.1:8000"
USERS = {
    "demo.hrms.alpha@example.com": {"company": "RD Demo HRMS Alpha Ltd", "module": "hrms",
                                    "allowed": ["/app/employee", "/app/leave-application", "/app/reckon-hrms", "/app"],
                                    "blocked": ["/app/sales-invoice", "/app/crm-lead"],
                                    "api_allowed": "Employee", "api_blocked": "Sales Invoice"},
    "demo.crm.alpha@example.com": {"company": "RD Demo CRM Alpha Ltd", "module": "crm",
                                   "allowed": ["/app/crm-lead", "/app/crm-deal", "/app"],
                                   "blocked": ["/app/employee", "/app/sales-invoice"],
                                   "api_allowed": "CRM Lead", "api_blocked": "Employee"},
}


def fetch(path, sid):
    req = urllib.request.Request(BASE + path, headers={"Host": SITE, "Cookie": f"sid={sid}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            return res.status, res.read(20000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(400).decode("utf-8", "replace")


frappe.init(site=SITE)
frappe.connect()
from werkzeug.test import EnvironBuilder
frappe.local.request = EnvironBuilder(path="/", base_url="http://" + SITE).get_request()
sids = {}
for email in USERS:
    frappe.local.login_manager = None
    LoginManager().login_as(email)
    sids[email] = frappe.session.sid
frappe.db.commit()

for email, spec in USERS.items():
    sid = sids[email]
    for path in spec["allowed"]:
        status, _ = fetch(path, sid)
        print("HTTP", email, path, status, "OK" if status == 200 else "UNEXPECTED")
    for path in spec["blocked"]:
        status, _ = fetch(path, sid)
        print("HTTP", email, path, status, "OK" if status in (403, 417) else "UNEXPECTED")
    q = urllib.parse.quote(spec["api_allowed"])
    status, body = fetch(f"/api/resource/{q}?limit_page_length=0&fields=%5B%22name%22%2C%22company%22%5D", sid)
    companies = sorted({row.get("company") for row in json.loads(body).get("data", [])}) if status == 200 else []
    print("API", email, spec["api_allowed"], status, companies, "OK" if companies in ([spec["company"]], []) and status == 200 else "UNEXPECTED")
    q = urllib.parse.quote(spec["api_blocked"])
    status, _ = fetch(f"/api/resource/{q}?limit_page_length=1", sid)
    print("API", email, spec["api_blocked"], status, "OK" if status in (403, 417) else "UNEXPECTED")

for email, sid in sids.items():
    frappe.db.delete("Sessions", {"sid": sid})
frappe.db.commit()
print("SESSIONS_REMOVED", len(sids))
