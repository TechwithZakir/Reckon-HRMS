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
    run = frappe.db.get_value("Payroll Entry", name, ["company", "start_date"], as_dict=True)
    return {
        "title": "Salary sheet (Paid statement)" if paid else "Salary sheet (Draft)",
        "status_word": "PAID STATEMENT" if paid else "DRAFT",
        "company": run.company,
        "month_label": run.start_date.strftime("%B %Y"),
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
    """Landscape salary sheet: earnings under TOTAL GROSS SALARY, deductions under TOTAL DEDUCTIONS."""
    from frappe.utils.pdf import get_pdf

    data = _table(name)
    esc = html_lib.escape
    earn = [c for c in data["columns"] if c["type"] == "Earning"]
    dedu = [c for c in data["columns"] if c["type"] == "Deduction"]

    group_row = (f"<tr><th rowspan='2'>SL</th><th rowspan='2' class='l'>ID</th><th rowspan='2' class='l'>Name of employee</th>"
                 f"<th colspan='{len(earn)}' class='grp'>TOTAL GROSS SALARY</th><th rowspan='2'>Gross</th>"
                 f"<th colspan='{len(dedu)}' class='grp'>TOTAL DEDUCTIONS</th><th rowspan='2'>Total deductions</th>"
                 f"<th rowspan='2'>Net payable</th><th rowspan='2' class='l'>Status</th></tr>")
    code_row = "<tr>" + "".join(f"<th title='{esc(c['name'])}'>{esc(c['code'])}</th>" for c in earn + dedu) + "</tr>"

    body = []
    for i, r in enumerate(data["rows"], start=1):
        earn_cells = "".join(f"<td>{r['components'].get(c['code'], 0):,.2f}</td>" for c in earn)
        dedu_cells = "".join(f"<td>{r['components'].get(c['code'], 0):,.2f}</td>" for c in dedu)
        body.append(f"<tr><td>{i}</td><td class='l'>{esc(r['employee'])}</td><td class='l'>{esc(r['employee_name'] or '')}</td>"
                    f"{earn_cells}<td>{r['gross']:,.2f}</td>{dedu_cells}<td>{r['deductions']:,.2f}</td>"
                    f"<td>{r['net']:,.2f}</td><td class='l'>{esc(r['status'])}{' (held)' if r['held'] else ''}</td></tr>")
    totals = {"gross": sum(r["gross"] for r in data["rows"]), "ded": sum(r["deductions"] for r in data["rows"]),
              "net": sum(r["net"] for r in data["rows"])}
    legend = "".join(f"<tr><td><b>{esc(l['code'])}</b></td><td>{esc(l['name'])}</td></tr>" for l in data["legend"])
    html = f"""<html><head><style>
      body {{ font-family: Arial, sans-serif; font-size: 9px; }}
      .company {{ text-align: center; font-size: 15px; font-weight: bold; }}
      .title {{ text-align: center; font-size: 12px; margin: 4px 0 2px 0; font-weight: bold; }}
      .status {{ text-align: center; font-size: 10px; margin-bottom: 6px; }}
      table {{ border-collapse: collapse; width: 100%; }}
      th, td {{ border: 1px solid #777; padding: 3px 4px; text-align: right; }}
      th {{ background: #eef2f1; text-align: center; }}
      th.grp {{ background: #dfe9e6; }}
      td.l, th.l {{ text-align: left; }}
      tr.total td {{ font-weight: bold; background: #f4f4f4; }}
      .legend {{ width: 55%; margin-top: 12px; }}
      .legend td {{ text-align: left; }}
    </style></head><body>
      <div class="company">{esc(data['company'])}</div>
      <div class="title">Salary Sheet for the month of {esc(data['month_label'])}</div>
      <div class="status">{esc(data['status_word'])} · Run {esc(name)} · Amounts in BDT</div>
      <table><thead>{group_row}{code_row}</thead>
        <tbody>{''.join(body)}
          <tr class="total"><td colspan='3' class='l'>Total</td>{''.join('<td></td>' for _ in earn)}
            <td>{totals['gross']:,.2f}</td>{''.join('<td></td>' for _ in dedu)}<td>{totals['ded']:,.2f}</td>
            <td>{totals['net']:,.2f}</td><td class='l'></td></tr>
        </tbody></table>
      <table class='legend'><thead><tr><th>Code</th><th class='l'>Pay item</th></tr></thead><tbody>{legend}</tbody></table>
    </body></html>"""
    pdf = get_pdf(html, {"orientation": "Landscape", "page-size": "A4"})
    frappe.local.response.filename = f"{name}-{'paid' if data['status_word'] == 'PAID STATEMENT' else 'draft'}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"
