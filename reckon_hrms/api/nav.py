"""The Reckon HRMS menu for the web pages (home and check-in), built from reckon_hrms.menu.

The desk left nav gets the same items from the Custom Sidebar. This endpoint serves the same groups to
pages outside the desk, and leaves out any DocType or report the signed-in user cannot read.
"""

from __future__ import annotations

import frappe

from reckon_hrms.menu import ICONS, MENU


def _desk_path(doctype: str) -> str:
    return "/app/" + doctype.lower().replace(" ", "-")


@frappe.whitelist(methods=["GET"])
def get_menu() -> dict:
    if frappe.session.user == "Guest":
        frappe.throw("Sign in to see the menu.", frappe.PermissionError)
    groups = []
    seen = set()
    for group, entries in MENU:
        items = []
        for entry in entries:
            if entry[0] == "URL":
                label, url = entry[2], entry[1]
            elif entry[0] == "DocType":
                label, url = entry[1], _desk_path(entry[1])
                if not frappe.db.exists("DocType", entry[1]) or not frappe.has_permission(entry[1], "read"):
                    continue
            else:
                label, url = entry[1], f"/app/query-report/{entry[1]}"
                if not frappe.db.exists("Report", entry[1]) or not frappe.has_permission("Report", "read", entry[1]):
                    continue
            if label in seen:
                continue
            seen.add(label)
            items.append({"label": label, "url": url, "icon": ICONS.get(label, "circle")})
        if items:
            groups.append({"label": group, "items": items})
    return {"groups": groups}
