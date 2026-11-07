"""Onboard two demo tenants on the HRMS Standard plan through the SaaS registration flow.

Email verification is marked complete by this script (no mail is sent on this site).
Passwords are random and printed once.
"""

import secrets
import sys

import frappe
from frappe.utils import now_datetime

from reckon_saas_platform.saas import provision_registration

DEMO = [
    ("RD Demo HRMS Alpha Ltd", "demo.hrms.alpha@example.com", "Alpha Owner"),
    ("RD Demo HRMS Beta Ltd", "demo.hrms.beta@example.com", "Beta Owner"),
]


def onboard(business_name, email, owner_name):
    existing = frappe.db.get_value("SaaS Registration", {"owner_email": email}, "name")
    if existing:
        return existing, None
    password = secrets.token_urlsafe(12)
    reg = frappe.get_doc(
        {
            "doctype": "SaaS Registration",
            "business_name": business_name,
            "owner_email": email,
            "owner_name": owner_name,
            "owner_password": password,
            "plan": "HRMS Standard",
            "saas_module": "hrms",
            "billing_cycle": "Monthly",
            "status": "Provisioning",
            "email_verified": 1,
            "verified_on": now_datetime(),
        }
    ).insert(ignore_permissions=True)
    frappe.db.commit()
    return reg.name, password


def main():
    for business_name, email, owner_name in DEMO:
        name, password = onboard(business_name, email, owner_name)
        provision_registration(name)
        frappe.db.commit()
        reg = frappe.get_doc("SaaS Registration", name)
        print("REG", name, reg.status, reg.company, reg.company_admin, reg.subscription)
        if password:
            print("DEMO_PASSWORD", email, password)


if __name__ == "__main__":
    frappe.init(site=sys.argv[1])
    frappe.connect()
    main()
