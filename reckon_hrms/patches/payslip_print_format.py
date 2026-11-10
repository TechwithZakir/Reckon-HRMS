"""Add the Reckon Payslip print format for a Salary Slip: one employee per page, Draft or Paid marked. Idempotent."""

import frappe

NAME = "Reckon Payslip"

HTML = """
<div style="font-family: Arial, sans-serif; font-size: 11px; color: #222;">
  <table style="width:100%; border-bottom:1px solid #bbb;">
    <tr>
      <td><div style="font-size:18px; font-weight:bold;">{{ frappe.db.get_value("Company", doc.company, "company_name") or doc.company }}</div>
          <div style="color:#666;">Salary slip &middot; {{ "PAID" if doc.reckon_payment_entry else ("ISSUED" if doc.docstatus == 1 else "DRAFT - NOT FOR ISSUE") }}</div></td>
      <td style="text-align:right;"><div style="color:#666;">Payslip for the month</div>
          <div style="font-size:16px; font-weight:bold;">{{ frappe.utils.formatdate(doc.start_date, "MMMM yyyy") }}</div></td>
    </tr>
  </table>

  <table style="width:100%; margin-top:14px;">
    <tr>
      <td style="vertical-align:top; width:55%;">
        <div style="font-weight:bold; color:#666;">EMPLOYEE SUMMARY</div>
        <table>
          <tr><td style="color:#666; padding:3px 12px 3px 0;">Employee name</td><td>: {{ doc.employee_name }}</td></tr>
          <tr><td style="color:#666; padding:3px 12px 3px 0;">Designation</td><td>: {{ doc.designation or "" }}</td></tr>
          <tr><td style="color:#666; padding:3px 12px 3px 0;">Employee ID</td><td>: {{ doc.employee }}</td></tr>
          <tr><td style="color:#666; padding:3px 12px 3px 0;">Pay period</td><td>: {{ frappe.utils.formatdate(doc.start_date, "MMMM yyyy") }}</td></tr>
          <tr><td style="color:#666; padding:3px 12px 3px 0;">Pay date</td><td>: {{ frappe.utils.formatdate(doc.posting_date) }}</td></tr>
        </table>
      </td>
      <td style="vertical-align:top;">
        <div style="border:1px solid #cfd8d5; border-radius:6px; padding:10px 14px; background:#f1f8f6;">
          <div style="font-size:22px; font-weight:bold; color:#1d5f4f;">{{ frappe.utils.fmt_money(doc.net_pay, currency=doc.currency) }}</div>
          <div style="color:#666;">Employee net pay</div>
          <table style="margin-top:8px;">
            <tr><td style="color:#666; padding-right:12px;">Paid days</td><td>: {{ doc.payment_days }}</td></tr>
            <tr><td style="color:#666; padding-right:12px;">LOP days</td><td>: {{ doc.leave_without_pay or 0 }}</td></tr>
          </table>
        </div>
      </td>
    </tr>
  </table>

  <table style="width:100%; border-collapse:collapse; margin-top:16px;">
    <tr>
      <th style="text-align:left; border-bottom:1px solid #999; padding:6px;">EARNINGS</th>
      <th style="text-align:right; border-bottom:1px solid #999; padding:6px;">AMOUNT</th>
      <th style="text-align:right; border-bottom:1px solid #999; padding:6px;">YTD</th>
      <th style="width:4%;"></th>
      <th style="text-align:left; border-bottom:1px solid #999; padding:6px;">DEDUCTIONS</th>
      <th style="text-align:right; border-bottom:1px solid #999; padding:6px;">AMOUNT</th>
      <th style="text-align:right; border-bottom:1px solid #999; padding:6px;">YTD</th>
    </tr>
    {% set earn = doc.earnings %}{% set dedu = doc.deductions %}
    {% for i in range(max(earn|length, dedu|length)) %}
    <tr>
      <td style="padding:6px; border-bottom:1px dotted #ccc;">{{ earn[i].salary_component if i < earn|length else "" }}</td>
      <td style="text-align:right; padding:6px; border-bottom:1px dotted #ccc;">{{ "{:,.2f}".format(earn[i].amount) if i < earn|length else "" }}</td>
      <td style="text-align:right; padding:6px; border-bottom:1px dotted #ccc;">{{ "{:,.2f}".format(earn[i].year_to_date or 0) if i < earn|length else "" }}</td>
      <td></td>
      <td style="padding:6px; border-bottom:1px dotted #ccc;">{{ dedu[i].salary_component if i < dedu|length else "" }}</td>
      <td style="text-align:right; padding:6px; border-bottom:1px dotted #ccc;">{{ "{:,.2f}".format(dedu[i].amount) if i < dedu|length else "" }}</td>
      <td style="text-align:right; padding:6px; border-bottom:1px dotted #ccc;">{{ "{:,.2f}".format(dedu[i].year_to_date or 0) if i < dedu|length else "" }}</td>
    </tr>
    {% endfor %}
    <tr style="font-weight:bold; background:#f5f6f7;">
      <td style="padding:6px;">Gross earnings</td><td style="text-align:right; padding:6px;">{{ "{:,.2f}".format(doc.gross_pay) }}</td><td></td>
      <td></td>
      <td style="padding:6px;">Total deductions</td><td style="text-align:right; padding:6px;">{{ "{:,.2f}".format(doc.total_deduction) }}</td><td></td>
    </tr>
  </table>

  <div style="margin-top:16px; border:1px solid #cfd8d5; border-radius:6px; padding:10px 14px; background:#f1f8f6;">
    <table style="width:100%;"><tr>
      <td><b>TOTAL NET PAYABLE</b><div style="color:#666;">Gross earnings &minus; total deductions</div></td>
      <td style="text-align:right; font-size:16px; font-weight:bold;">{{ frappe.utils.fmt_money(doc.net_pay, currency=doc.currency) }}</td>
    </tr></table>
  </div>
  <div style="text-align:right; margin-top:10px;"><span style="color:#666;">Amount in words:</span> {{ frappe.utils.money_in_words(doc.net_pay, doc.currency) }}</div>
  <div style="text-align:center; color:#777; margin-top:22px; font-size:10px;">This payslip is generated automatically; a signature is not required.</div>
</div>
"""


def execute():
    if frappe.db.exists("Print Format", NAME):
        return
    frappe.get_doc({
        "doctype": "Print Format", "name": NAME, "doc_type": "Salary Slip", "module": "Reckon HRMS",
        "print_format_type": "Jinja", "custom_format": 1, "standard": "No", "html": HTML,
        "orientation": "Portrait", "disabled": 0,
    }).insert(ignore_permissions=True)
