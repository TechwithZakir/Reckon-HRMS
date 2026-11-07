"""Arrange the whole Reckon HRMS desk menu under /desk/reckon-hrms and hide the stock Frappe HR workspaces.

Groups follow the work an HR owner does. The sidebar lists DocTypes and Reports. Pages that live outside
the Desk (my home, check-in) are URL shortcuts, because workspace links only accept DocType, Page or Report
targets. The desk content blocks are rebuilt from the same menu. Stock Frappe HR workspaces are hidden so
tenants only see the Reckon HRMS menu. Idempotent.
"""

import json

import frappe

WORKSPACE = "Reckon HRMS"

# (group, items). Items: ("DocType", name) | ("Report", name) | ("URL", path, label)
MENU = (
    ("Featured", (
        ("URL", "/hrms-home", "My home"),
        ("URL", "/hrms-checkin", "Check in / out"),
        ("DocType", "Leave Application"),
        ("DocType", "Expense Claim"),
        ("DocType", "Payroll Entry"),
        ("DocType", "Employee"),
    )),
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
        ("Report", "Monthly Attendance Sheet"),
    )),
    ("Leave & Approvals", (
        ("DocType", "Leave Application"),
        ("DocType", "Leave Type"),
        ("DocType", "Leave Allocation"),
        ("DocType", "Expense Claim"),
        ("DocType", "Expense Claim Type"),
        ("Report", "Employee Leave Balance"),
    )),
    ("Payroll", (
        ("DocType", "Salary Structure"),
        ("DocType", "Salary Structure Assignment"),
        ("DocType", "Salary Component"),
        ("DocType", "Additional Salary"),
        ("DocType", "Payroll Entry"),
        ("DocType", "Salary Slip"),
        ("Report", "Salary Register"),
    )),
)

STOCK_HR_NAMES = ("Frappe HR", "HR", "HR Setup", "Human Resources", "Frappe HRMS", "HRMS", "Payroll", "Tax & Benefits")


def _item_label(item) -> str:
    return item[2] if item[0] == "URL" else item[1]


def _exists(item) -> bool:
    if item[0] == "DocType":
        return frappe.db.exists("DocType", item[1])
    if item[0] == "Report":
        return frappe.db.exists("Report", item[1])
    return True


def _link_rows() -> list[dict]:
    rows = []
    for group, items in MENU:
        rows.append({"type": "Card Break", "label": group})
        for item in items:
            if item[0] == "URL" or not _exists(item):
                continue
            if item[0] == "DocType":
                rows.append({"type": "Link", "link_type": "DocType", "link_to": item[1], "label": item[1]})
            else:
                rows.append({"type": "Link", "link_type": "Report", "link_to": item[1], "label": item[1]})
    return rows


def _shortcut_rows() -> list[dict]:
    rows = []
    for _group, items in MENU:
        for item in items:
            if not _exists(item):
                continue
            if item[0] == "URL":
                rows.append({"type": "URL", "url": item[1], "label": item[2], "color": "Blue"})
            elif item[0] == "DocType":
                rows.append({"type": "DocType", "link_to": item[1], "label": item[1], "color": "Blue"})
            else:
                rows.append({"type": "Report", "link_to": item[1], "label": item[1], "color": "Blue"})
    return rows


def _content_blocks() -> list[dict]:
    blocks = []
    for index, (group, items) in enumerate(MENU):
        blocks.append({"id": f"rhrms-h{index}", "type": "header",
                       "data": {"text": f'<span class="h4">{group}</span>', "col": 12}})
        for item in items:
            if not _exists(item):
                continue
            label = _item_label(item)
            blocks.append({"id": f"rhrms-s-{label.replace(' ', '-').replace('/', '-').lower()}",
                           "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})
    return blocks


def _rebuild_workspace():
    if not frappe.db.exists("Workspace", WORKSPACE):
        return
    ws = frappe.get_doc("Workspace", WORKSPACE)
    links = _link_rows()
    shortcuts = _shortcut_rows()
    blocks = _content_blocks()

    current_links = [(r.type, r.label, r.link_to) for r in ws.links]
    if current_links != [(r["type"], r["label"], r.get("link_to")) for r in links]:
        ws.set("links", [])
        for row in links:
            ws.append("links", row)
    current_short = [(r.type, r.label, r.link_to or r.url) for r in ws.shortcuts]
    if current_short != [(r["type"], r["label"], r.get("link_to") or r.get("url")) for r in shortcuts]:
        ws.set("shortcuts", [])
        for row in shortcuts:
            ws.append("shortcuts", row)
    ws.content = json.dumps(blocks)
    ws.is_hidden = 0
    ws.save(ignore_permissions=True)


def _hide_frappe_hr():
    names = set(frappe.get_all("Workspace", filters={"name": ["in", list(STOCK_HR_NAMES)]}, pluck="name"))
    names |= set(frappe.get_all("Workspace", filters={"module": ["in", ["HR", "HRMS", "Human Resources"]]},
                                pluck="name"))
    names.discard(WORKSPACE)
    for name in names:
        if frappe.db.get_value("Workspace", name, "is_hidden") != 1:
            frappe.db.set_value("Workspace", name, "is_hidden", 1)


def execute():
    _rebuild_workspace()
    _hide_frappe_hr()
    frappe.clear_cache()
