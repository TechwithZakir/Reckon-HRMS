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
from reckon_hrms.menu import ICONS, MENU  # noqa: E402  (single source for the menu)

STOCK_HR_NAMES = ("Frappe HR", "HR", "HR Setup", "Human Resources", "Frappe HRMS", "HRMS", "Payroll", "Tax & Benefits")


def _item_label(item) -> str:
    return item[2] if item[0] in ("URL", "Page") else item[1]


def _exists(item) -> bool:
    if item[0] == "DocType":
        return frappe.db.exists("DocType", item[1])
    if item[0] == "Report":
        return frappe.db.exists("Report", item[1])
    if item[0] == "Page":
        return frappe.db.exists("Page", item[1])
    return True


# Web pages reached from the sidebar through a desk Page that redirects to them (see page/ folders).
PAGE_FOR_URL = {"/hrms-home": "reckon-hrms-home", "/hrms-checkin": "reckon-hrms-checkin"}


def _link_rows() -> list[dict]:
    rows = []
    seen = set()
    for group, items in MENU:
        rows.append({"type": "Card Break", "label": group})
        for item in items:
            if item[0] == "URL":
                # Web pages live in the cards and the left nav as URLs, not as workspace links.
                continue
            if not _exists(item):
                continue
            if item[0] == "DocType":
                rows.append({"type": "Link", "link_type": "DocType", "link_to": item[1], "label": item[1]})
            elif item[0] == "Page":
                rows.append({"type": "Link", "link_type": "Page", "link_to": item[1], "label": item[2]})
            else:
                rows.append({"type": "Link", "link_type": "Report", "link_to": item[1], "label": item[1]})
    return rows


def _shortcut_rows() -> list[dict]:
    rows = []
    seen = set()
    for _group, items in MENU:
        for item in items:
            if not _exists(item) or _item_label(item) in seen:
                continue
            seen.add(_item_label(item))
            if item[0] == "URL":
                rows.append({"type": "URL", "url": item[1], "label": item[2], "color": "Blue"})
            elif item[0] == "DocType":
                rows.append({"type": "DocType", "link_to": item[1], "label": item[1], "color": "Blue"})
            elif item[0] == "Page":
                rows.append({"type": "Page", "link_to": item[1], "label": item[2], "color": "Blue"})
            else:
                rows.append({"type": "Report", "link_to": item[1], "label": item[1], "color": "Blue"})
    return rows


def _content_blocks() -> list[dict]:
    blocks = []
    seen = set()
    for index, (group, items) in enumerate(MENU):
        blocks.append({"id": f"rhrms-h{index}", "type": "header",
                       "data": {"text": f'<span class="h4">{group}</span>', "col": 12}})
        for item in items:
            if not _exists(item) or _item_label(item) in seen:
                continue
            seen.add(_item_label(item))
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


def _sidebar_items() -> list[dict]:
    """Left-nav items: a section per group, then one link per menu entry (web pages, DocTypes, reports)."""
    items = []
    seen = set()
    for group, entries in MENU:
        items.append({"type": "Section Break", "label": group, "collapsible": 1})
        for entry in entries:
            if entry[0] == "URL":
                if entry[2] in seen:
                    continue
                seen.add(entry[2])
                items.append({"type": "Link", "label": entry[2], "link_type": "URL", "url": entry[1],
                              "icon": ICONS.get(entry[2], "circle")})
                continue
            if entry[0] == "Page":
                if not _exists(entry) or entry[2] in seen:
                    continue
                seen.add(entry[2])
                items.append({"type": "Link", "label": entry[2], "link_type": "Page", "link_to": entry[1],
                              "icon": ICONS.get(entry[2], "circle")})
                continue
            if not _exists(entry) or entry[1] in seen:
                continue
            seen.add(entry[1])
            link_type = "DocType" if entry[0] == "DocType" else "Report"
            items.append({"type": "Link", "label": entry[1], "link_type": link_type, "link_to": entry[1],
                          "icon": ICONS.get(entry[1], "circle")})
    return items


def _rebuild_sidebar():
    """Create or refresh the module Sidebar that drives the Reckon HRMS left nav (Frappe 16 model)."""
    if not frappe.db.exists("Module Def", WORKSPACE):
        return
    # The app owns the Reckon HRMS Sidebar, so the site customizes it through Custom Sidebar (site-wide).
    items = _sidebar_items()
    existing = frappe.db.get_value("Custom Sidebar", {"module": WORKSPACE, "user": ["is", "not set"]}, "name")
    if existing:
        custom = frappe.get_doc("Custom Sidebar", existing)
        custom.set("sidebar_items", [])
    else:
        custom = frappe.get_doc({"doctype": "Custom Sidebar", "module": WORKSPACE, "label": WORKSPACE,
                                 "header_icon": "users"})
    for row in items:
        row["added"] = 1  # Frappe treats only added rows as items; other rows are references to base items
        if row["type"] == "Link":
            row["indent"] = 1  # links sit under the section heading above them
        custom.append("sidebar_items", row)
    if existing:
        custom.save(ignore_permissions=True)
    else:
        custom.insert(ignore_permissions=True)


def execute():
    _rebuild_workspace()
    _rebuild_sidebar()
    _hide_frappe_hr()
    frappe.clear_cache()
