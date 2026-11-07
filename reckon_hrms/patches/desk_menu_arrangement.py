"""Arrange the whole Reckon HRMS desk menu under /desk/reckon-hrms and hide the stock Frappe HR workspaces.

Groups follow the work an HR owner does: Home, People, Time & Attendance, Leave & Approvals, Payroll,
Statutory and Setup. Pages that live outside the Desk (home, check-in) are added as URL links. Stock
Frappe HR workspaces are hidden from the sidebar so tenants only see the Reckon HRMS menu. Idempotent.
"""

import json

import frappe

WORKSPACE = "Reckon HRMS"

MENU = (
    ("Home", (
        ("URL", "/hrms-home", "My home"),
        ("URL", "/hrms-checkin", "Check in / out"),
    )),
    ("People", (
        ("DocType", "Employee"),
        ("DocType", "Department"),
        ("DocType", "Designation"),
        ("DocType", "HRMS Office Location"),
    )),
    ("Time & Attendance", (
        ("DocType", "Attendance"),
        ("DocType", "Employee Checkin"),
        ("DocType", "Shift Type"),
        ("DocType", "Shift Assignment"),
        ("DocType", "Holiday List"),
        ("DocType", "Holiday List Assignment"),
    )),
    ("Leave & Approvals", (
        ("DocType", "Leave Application"),
        ("DocType", "Leave Type"),
        ("DocType", "Leave Allocation"),
        ("DocType", "Expense Claim"),
        ("DocType", "Expense Claim Type"),
        ("URL", "/app/query-report/Employee Leave Balance", "Leave balance"),
    )),
    ("Payroll", (
        ("DocType", "Salary Structure"),
        ("DocType", "Salary Structure Assignment"),
        ("DocType", "Salary Component"),
        ("DocType", "Additional Salary"),
        ("DocType", "Payroll Entry"),
        ("DocType", "Salary Slip"),
        ("URL", "/app/query-report/Salary Register", "Salary register"),
    )),
    ("Reports", (
        ("URL", "/app/query-report/Monthly Attendance Sheet", "Monthly attendance sheet"),
        ("URL", "/app/query-report/Salary Register", "Salary register"),
        ("URL", "/app/query-report/Employee Leave Balance", "Leave balance"),
    )),
)


def _menu_rows():
    rows = []
    for group, items in MENU:
        rows.append({"type": "Card Break", "label": group})
        for item in items:
            kind = item[0]
            if kind == "URL":
                _, url, label = item
                rows.append({"type": "URL", "link_to": url, "label": label})
            else:
                doctype = item[1]
                if frappe.db.exists("DocType", doctype):
                    rows.append({"type": "Link", "link_type": "DocType", "link_to": doctype, "label": doctype})
    return rows


def _shortcut_rows():
    rows = []
    for row in _menu_rows():
        if row["type"] == "Link":
            rows.append({"type": "DocType", "link_to": row["link_to"], "label": row["label"], "color": "Blue"})
    return rows


def _rebuild_workspace():
    if not frappe.db.exists("Workspace", WORKSPACE):
        return
    ws = frappe.get_doc("Workspace", WORKSPACE)
    links = _menu_rows()
    shortcuts = _shortcut_rows()
    current = [(r.type, r.label, r.link_to) for r in ws.links]
    target = [(r["type"], r["label"], r.get("link_to")) for r in links]
    if current != target:
        ws.set("links", [])
        for row in links:
            ws.append("links", row)
    if len(ws.shortcuts) != len(shortcuts):
        ws.set("shortcuts", [])
        for row in shortcuts:
            ws.append("shortcuts", row)
    ws.is_hidden = 0
    ws.save(ignore_permissions=True)


STOCK_HR_NAMES = ("Frappe HR", "HR", "HR Setup", "Human Resources", "Frappe HRMS", "HRMS")


def _hide_frappe_hr():
    names = set(frappe.get_all("Workspace", filters={"name": ["in", list(STOCK_HR_NAMES)]}, pluck="name"))
    names |= set(frappe.get_all("Workspace", filters={"module": ["in", ["HR", "HRMS", "Human Resources"]]},
                                pluck="name"))
    names |= set(frappe.get_all("Workspace", filters={"name": ["like", "%HR%"]}, pluck="name"))
    names.discard(WORKSPACE)
    for name in names:
        if frappe.db.get_value("Workspace", name, "is_hidden") != 1:
            frappe.db.set_value("Workspace", name, "is_hidden", 1)


def execute():
    _rebuild_workspace()
    _hide_frappe_hr()
    frappe.clear_cache()
