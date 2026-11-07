"""Set up the CRM SaaS plan and demo tenants, then test CRM company isolation.

Usage on the bench: python crm_tenants.py <site> [setup|test]
Demo records carry the "RD Demo CRM" prefix.
"""

import secrets
import sys

import frappe
from frappe.utils import now_datetime

PLAN = {
    "plan_name": "CRM Standard",
    "saas_module": "crm",
    "plan_version": 1,
    "currency": "BDT",
    "price": 1000,
    "billing_cycle": "Monthly",
    "trial_days": 15,
    "grace_days": 5,
    "enabled": 1,
}
DEMO = [
    ("RD Demo CRM Alpha Ltd", "demo.crm.alpha@example.com", "CRM Alpha Owner"),
    ("RD Demo CRM Beta Ltd", "demo.crm.beta@example.com", "CRM Beta Owner"),
]


def setup():
    from reckon_saas_platform.module_registry import sync_saas_modules
    from reckon_saas_platform.saas import provision_registration

    print("SYNCED", sync_saas_modules())
    if not frappe.db.exists("SaaS Plan", PLAN["plan_name"]):
        frappe.get_doc({"doctype": "SaaS Plan", **PLAN}).insert(ignore_permissions=True)
    frappe.db.commit()
    for business, email, owner in DEMO:
        existing = frappe.db.get_value("SaaS Registration", {"owner_email": email}, "name")
        if existing:
            name = existing
        else:
            reg = frappe.get_doc({
                "doctype": "SaaS Registration", "business_name": business,
                "owner_email": email, "owner_name": owner,
                "owner_password": secrets.token_urlsafe(12),
                "plan": PLAN["plan_name"], "saas_module": "crm", "billing_cycle": "Monthly",
                "status": "Provisioning", "email_verified": 1, "verified_on": now_datetime(),
            }).insert(ignore_permissions=True)
            frappe.db.commit()
            name = reg.name
        provision_registration(name)
        frappe.db.commit()
        reg = frappe.get_doc("SaaS Registration", name)
        print("REG", name, reg.status, reg.company, reg.subscription)


def test():
    from reckon_saas_platform.saas import is_subscription_active

    names = {"RD Demo CRM Alpha Ltd": ["Alpha Lead One", "Alpha Lead Two"],
             "RD Demo CRM Beta Ltd": ["Beta Lead One", "Beta Lead Two"]}
    emails = {"RD Demo CRM Alpha Ltd": "demo.crm.alpha@example.com",
              "RD Demo CRM Beta Ltd": "demo.crm.beta@example.com"}
    for company, email in emails.items():
        frappe.set_user(email)
        try:
            for full in names[company]:
                first, _, last = full.partition(" ")
                if not frappe.db.exists("CRM Lead", {"first_name": first, "last_name": last, "company": company}):
                    frappe.get_doc({"doctype": "CRM Lead", "first_name": first, "last_name": last,
                                    "email": f"{first}.{last}".replace(" ", "").lower() + "@example.com"}).insert()
        finally:
            frappe.set_user("Administrator")
    frappe.db.commit()
    for company, email in emails.items():
        frappe.set_user(email)
        try:
            rows = frappe.get_list("CRM Lead", fields=["name", "company"], limit_page_length=0)
            print("VISIBLE", email, sorted({r.company for r in rows}), len(rows))
        finally:
            frappe.set_user("Administrator")
        print("SUBSCRIBED", company, is_subscription_active(company, "crm"))
    alpha_lead = frappe.db.get_value("CRM Lead", {"company": "RD Demo CRM Alpha Ltd"}, "name")
    beta_lead = frappe.db.get_value("CRM Lead", {"company": "RD Demo CRM Beta Ltd"}, "name")
    frappe.set_user(emails["RD Demo CRM Alpha Ltd"])
    try:
        frappe.get_doc("CRM Lead", beta_lead).check_permission("read")
        print("CROSS_READ ALLOWED (BAD)")
    except frappe.PermissionError:
        print("CROSS_READ denied (OK)")
    finally:
        frappe.set_user("Administrator")
    print("OWN_READ", alpha_lead is not None)


if __name__ == "__main__":
    frappe.init(site=sys.argv[1])
    frappe.connect()
    (test if len(sys.argv) > 2 and sys.argv[2] == "test" else setup)()
