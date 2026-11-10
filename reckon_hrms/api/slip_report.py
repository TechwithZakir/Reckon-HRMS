"""Slip table and PDF for a salary run: every component as a two-character column, landscape.

The title reads "Draft" while no slip is paid, and "Paid" as a salary statement once any slip has a
payment journal entry.
"""

from __future__ import annotations

import html as html_lib

import frappe
from frappe import _
from frappe.utils import flt

from reckon_hrms.api.payroll_run import _gate
from reckon_hrms.slip_codes import short_codes


def _table(name: str) -> dict:
    _gate("Payroll Entry", "read")
    slips = frappe.get_all("Salary Slip", filters={"payroll_entry": name, "docstatus": ["!=", 2]},
                           fields=["name", "employee", "employee_name", "docstatus", "gross_pay",
                                   "total_deduction", "net_pay", "reckon_payment_entry", "reckon_payment_hold"],
                           order_by="employee asc", limit_page_length=0)
    if not slips:
        frappe.throw(_("No salary slips for this run yet."))
    details = frappe.get_all("Salary Detail", filters={"parent": ["in", [s.name for s in slips]],
                                                       "parenttype": "Salary Slip"},
                             fields=["parent", "salary_component", "amount", "parentfield"],
                             order_by="idx asc", limit_page_length=0)

    # Earnings first, then deductions, each in the order the structure lists them.
    names: list[str] = []
    kinds: dict[str, str] = {}
    for row in details:
        if row.salary_component not in kinds:
            kinds[row.salary_component] = "Deduction" if row.parentfield == "deductions" else "Earning"
    for kind in ("Earning", "Deduction"):
        names += [c for c, k in kinds.items() if k == kind]
    codes = short_codes(names)

    by_slip: dict[str, dict[str, float]] = {s.name: {} for s in slips}
    for row in details:
        bucket = by_slip.setdefault(row.parent, {})
        code = codes[row.salary_component]
        bucket[code] = round(bucket.get(code, 0.0) + flt(row.amount), 2)

    rows = []
    for s in slips:
        if s.reckon_payment_entry:
            status = "Paid"
        elif s.docstatus == 1:
            status = "Submitted"
        else:
            status = "Draft"
        rows.append({
            "employee": s.employee, "employee_name": s.employee_name, "status": status,
            "held": bool(s.reckon_payment_hold), "components": by_slip.get(s.name, {}),
            "gross": flt(s.gross_pay), "deductions": flt(s.total_deduction), "net": flt(s.net_pay),
        })

    paid = any(r["status"] == "Paid" for r in rows)
    return {
        "title": "Salary statement (Paid)" if paid else "Draft pay slips (Draft)",
        "run": name,
        "columns": [{"code": codes[n], "name": n, "type": kinds[n]} for n in names],
        "rows": rows,
        "legend": [{"code": codes[n], "name": n} for n in names],
    }


@frappe.whitelist(methods=["GET"])
def slip_table(name: str) -> dict:
    """Every slip in the run with each component as a two-character column."""
    return _table(name)


@frappe.whitelist(methods=["GET"])
def slip_pdf(name: str):
    """Landscape PDF of the slip table, with a legend for the two-character codes."""
    from frappe.utils.pdf import get_pdf

    data = _table(name)
    esc = html_lib.escape
    head = "".join(f"<th>{esc(c['code'])}</th>" for c in data["columns"])
    body = []
    for i, r in enumerate(data["rows"], start=1):
        cells = "".join(f"<td>{r['components'].get(c['code'], 0):,.2f}</td>" for c in data["columns"])
        body.append(f"<tr><td>{i}</td><td class='l'>{esc(r['employee'])}</td><td class='l'>{esc(r['employee_name'] or '')}</td>"
                    f"{cells}<td>{r['gross']:,.2f}</td><td>{r['deductions']:,.2f}</td><td>{r['net']:,.2f}</td>"
                    f"<td class='l'>{esc(r['status'])}{' (held)' if r['held'] else ''}</td></tr>")
    legend = "".join(f"<tr><td><b>{esc(l['code'])}</b></td><td>{esc(l['name'])}</td></tr>" for l in data["legend"])
    html = f"""<html><head><style>
      body {{ font-family: Arial, sans-serif; font-size: 9px; }}
      h1 {{ font-size: 15px; margin: 0 0 4px 0; }}
      table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
      th, td {{ border: 1px solid #999; padding: 3px 4px; text-align: right; }}
      th {{ background: #eef2f1; }}
      td.l, th.l {{ text-align: left; }}
      .legend {{ width: 60%; margin-top: 12px; }}
      .legend td {{ text-align: left; }}
    </style></head><body>
      <h1>{esc(data['title'])}</h1>
      <div>Run {esc(name)}. Amounts in BDT. Codes are explained at the end.</div>
      <table><thead><tr><th>#</th><th class='l'>ID</th><th class='l'>Name</th>{head}
        <th>Gross</th><th>Deductions</th><th>Net pay</th><th class='l'>Status</th></tr></thead>
        <tbody>{''.join(body)}</tbody></table>
      <h1 style="margin-top:14px;font-size:11px">Codes</h1>
      <table class='legend'><tbody>{legend}</tbody></table>
    </body></html>"""
    pdf = get_pdf(html, {"orientation": "Landscape", "page-size": "A4"})
    frappe.local.response.filename = f"{name}-{'paid' if 'Paid' in data['title'] else 'draft'}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"
