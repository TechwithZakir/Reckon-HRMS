"""Rebuild the Reckon HRMS workspace content so the four module groups render.

The workspace renders its content blocks, so each group gets a header block followed by
shortcut blocks for its DocTypes. The shortcut list is rebuilt to match. Idempotent.
"""

import json

import frappe

from reckon_hrms.patches.holiday_list_and_workspace import WORKSPACE, WORKSPACE_GROUPS


def _blocks():
    blocks = []
    for index, (group, doctypes) in enumerate(WORKSPACE_GROUPS):
        blocks.append({
            "id": f"rhrms-h{index}",
            "type": "header",
            "data": {"text": f'<span class="h4">{group}</span>', "col": 12},
        })
        for doctype in doctypes:
            if frappe.db.exists("DocType", doctype):
                blocks.append({
                    "id": f"rhrms-s-{doctype.replace(' ', '-').lower()}",
                    "type": "shortcut",
                    "data": {"shortcut_name": doctype, "col": 3},
                })
    return blocks


def execute():
    if not frappe.db.exists("Workspace", WORKSPACE):
        return
    ws = frappe.get_doc("Workspace", WORKSPACE)
    shortcuts = []
    for _group, doctypes in WORKSPACE_GROUPS:
        for doctype in doctypes:
            if frappe.db.exists("DocType", doctype):
                shortcuts.append({"type": "DocType", "link_to": doctype, "label": doctype, "color": "Blue"})
    blocks = _blocks()
    if json.loads(ws.content or "[]") == blocks and len(ws.shortcuts) == len(shortcuts):
        return
    ws.set("shortcuts", [])
    for row in shortcuts:
        ws.append("shortcuts", row)
    ws.content = json.dumps(blocks)
    ws.save(ignore_permissions=True)
    frappe.clear_cache()
