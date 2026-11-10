"""Bangladesh SME payroll on Frappe HRMS: setup, tax on salary slips, festival bonus, bilingual slips, bank sheet."""

from __future__ import annotations

import csv
import io

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from reckon_hrms import bd_payroll as bd

STRUCTURE_PREFIX = "Reckon BD SME"
FESTIVAL_COMPONENT = "Festival Bonus"
FESTIVAL_ABBR = "FESTIVAL"
PRINT_FORMAT = "Reckon Payslip (Bilingual)"

# Earnings and deductions of the starter structure. Formulas use the structure base and earlier rows.
EARNINGS = (
    {"salary_component": "Basic Salary", "abbr": "BASIC", "formula": "base * 0.6", "depends_on_payment_days": 1},
    {"salary_component": "House Rent Allowance", "abbr": "HRA", "formula": "BASIC * 0.5", "depends_on_payment_days": 0},
    {"salary_component": "Medical Allowance", "abbr": "MED", "amount": 1500},
    {"salary_component": "Conveyance Allowance", "abbr": "CONV", "amount": 1000},
)
DEDUCTIONS = (
    {"salary_component": "Provident Fund (Employee)", "abbr": "PFEMP", "formula": "BASIC * 0.05", "depends_on_payment_days": 0},
    # Filled in by apply_bd_tax on every slip, so the formula is a placeholder.
    {"salary_component": "Income Tax (TDS)", "abbr": "TDS", "amount": 0},
    # Zero in the structure; the late and early deduction for each run is an approved Additional Salary.
    # Having it here lets that record overwrite the structure amount on the slip.
    {"salary_component": "Late and Early Deduction", "abbr": "LATEDED", "amount": 0},
)


def structure_name(company: str) -> str:
    return f"{STRUCTURE_PREFIX} - {company}"[:140]


def ensure_payroll_payable(company: str) -> str | None:
    """Make sure the company has a payroll payable account and make it the company default. Idempotent.

    A payroll run cannot be created without it: HRMS posts the net pay accrual to this account.
    An existing "Payroll Payable" account is reused; otherwise one is created under the company's
    current liabilities. Returns None only when the company has no liabilities group to put it under.
    """
    current = frappe.db.get_value("Company", company, "default_payroll_payable_account")
    if current:
        return current
    account = frappe.db.get_value("Account", {"company": company, "is_group": 0,
                                              "account_name": ["like", "Payroll Payable%"]}, "name")
    if not account:
        parent = None
        payable = frappe.db.get_value("Company", company, "default_payable_account")
        if payable:
            parent = frappe.db.get_value("Account", payable, "parent_account")
        if not parent:
            parent = frappe.db.get_value("Account", {"company": company, "is_group": 1, "root_type": "Liability",
                                                     "account_name": ["like", "Current Liabilities%"]}, "name")
        if not parent:
            return None
        account = frappe.get_doc({"doctype": "Account", "account_name": "Payroll Payable", "company": company,
                                  "parent_account": parent, "account_type": "Payable", "is_group": 0}
                                 ).insert(ignore_permissions=True).name
    frappe.db.set_value("Company", company, "default_payroll_payable_account", account)
    return account


@frappe.whitelist(methods=["POST"])
def setup_bd_payroll(company: str) -> dict:
    """Create the Bangladesh starter components, salary structure and bilingual slip format. Idempotent."""
    frappe.only_for(["HR Manager", "Payroll Manager", "System Manager"])
    created = {"components": 0, "structure": False, "print_format": False}

    if not frappe.db.exists("Salary Component", FESTIVAL_COMPONENT):
        frappe.get_doc({"doctype": "Salary Component", "salary_component": FESTIVAL_COMPONENT,
                        "salary_component_abbr": FESTIVAL_ABBR, "type": "Earning"}).insert(ignore_permissions=True)
        created["components"] += 1

    # HRMS copies the payment-day flag from the component master, so align the masters with the rows.
    for row in EARNINGS + DEDUCTIONS:
        if "depends_on_payment_days" in row and frappe.db.exists("Salary Component", row["salary_component"]):
            frappe.db.set_value("Salary Component", row["salary_component"], "depends_on_payment_days",
                                row["depends_on_payment_days"])

    # HRMS resolves holidays from Holiday List Assignment, so the company calendar needs a submitted
    # company-level assignment. It covers every employee without a personal assignment.
    created["holiday_assignment"] = False
    calendar = frappe.db.get_value("Holiday List", {"company": company}, ["name", "from_date"],
                                   as_dict=True, order_by="from_date desc")
    if calendar and not frappe.db.exists("Holiday List Assignment", {"assigned_to": company,
                                         "applicable_for": "Company", "docstatus": 1}):
        hla = frappe.get_doc({"doctype": "Holiday List Assignment", "applicable_for": "Company",
                              "assigned_to": company, "holiday_list": calendar.name,
                              "from_date": calendar.from_date})
        hla.insert(ignore_permissions=True)
        hla.submit()
        created["holiday_assignment"] = True

    from reckon_hrms import industry_seed

    industry_seed._component("Late and Early Deduction")
    name = structure_name(company)
    if not frappe.db.exists("Salary Structure", name):
        earnings = [dict(row, amount_based_on_formula=1 if "formula" in row else 0,
                         formula=row.get("formula", ""), amount=row.get("amount", 0)) for row in EARNINGS]
        deductions = [dict(row, amount_based_on_formula=1 if "formula" in row else 0,
                           formula=row.get("formula", ""), amount=row.get("amount", 0)) for row in DEDUCTIONS]
        structure = frappe.get_doc({
            "doctype": "Salary Structure", "name": name, "company": company, "is_active": "Yes",
            "payroll_frequency": "Monthly", "earnings": earnings, "deductions": deductions,
        }).insert(ignore_permissions=True)
        structure.submit()  # assignments and slips only accept a submitted structure
        created["structure"] = True
    elif frappe.db.get_value("Salary Structure", name, "docstatus") == 0:
        frappe.get_doc("Salary Structure", name).submit()
        created["structure"] = True

    if not frappe.db.exists("Print Format", PRINT_FORMAT):
        frappe.get_doc({"doctype": "Print Format", "name": PRINT_FORMAT, "doc_type": "Salary Slip",
                        "print_format_type": "Jinja", "custom_format": 1, "standard": "No",
                        "html": bilingual_slip_html()}).insert(ignore_permissions=True)
        created["print_format"] = True

    created["payroll_payable"] = ensure_payroll_payable(company)
    frappe.db.commit()
    return created


def bilingual_slip_html() -> str:
    """Jinja template for a two-language slip. Labels come from bd_payroll.LABELS."""
    labels = "{" + ", ".join(f'"{k}": ("{en}", "{bn}")' for k, (en, bn) in bd.LABELS.items()) + "}"
    return f"""
{{% set L = {labels} %}}
<div style="font-family: 'Noto Sans Bengali', 'Nirmala UI', sans-serif; max-width: 720px; margin: auto">
  <h2 style="margin-bottom:0">{{{{ doc.company }}}}</h2>
  <div>{{{{ _("Salary Slip") }}}} / বেতন স্লিপ · {{{{ doc.start_date }}}} → {{{{ doc.end_date }}}}</div>
  <table style="width:100%; margin-top:12px; border-collapse:collapse">
    <tr><td>{{{{ _("Employee") }}}} / কর্মী</td><td>{{{{ doc.employee_name }}}} ({{{{ doc.employee }}}})</td></tr>
    <tr><td>{{{{ _("Designation") }}}} / পদবি</td><td>{{{{ doc.designation or "" }}}}</td></tr>
    <tr><td>{{{{ _("Department") }}}} / বিভাগ</td><td>{{{{ doc.department or "" }}}}</td></tr>
  </table>
  <table style="width:100%; margin-top:14px; border-collapse:collapse" border="1" cellpadding="6">
    <tr><th align="left">{{{{ _("Earnings") }}}} / আয়</th><th align="right">{{{{ _("Amount") }}}} / টাকা</th>
        <th align="left">{{{{ _("Deductions") }}}} / কর্তন</th><th align="right">{{{{ _("Amount") }}}} / টাকা</th></tr>
    {{% for e in doc.earnings %}}{{% set d = doc.deductions[loop.index0] if loop.index0 < doc.deductions|length else None %}}
    <tr>
      <td>{{{{ L.get(e.salary_component, (e.salary_component, e.salary_component))[0] }}}} / {{{{ L.get(e.salary_component, (e.salary_component, e.salary_component))[1] }}}}</td>
      <td align="right">{{{{ "{{:,.2f}}".format(e.amount) }}}}</td>
      <td>{{% if d %}}{{{{ L.get(d.salary_component, (d.salary_component, d.salary_component))[0] }}}} / {{{{ L.get(d.salary_component, (d.salary_component, d.salary_component))[1] }}}}{{% endif %}}</td>
      <td align="right">{{% if d %}}{{{{ "{{:,.2f}}".format(d.amount) }}}}{{% endif %}}</td>
    </tr>
    {{% endfor %}}
    <tr><td><b>{{{{ _("Gross Pay") }}}} / মোট আয়</b></td><td align="right"><b>{{{{ "{{:,.2f}}".format(doc.gross_pay) }}}}</b></td>
        <td><b>{{{{ _("Total Deduction") }}}} / মোট কর্তন</b></td><td align="right"><b>{{{{ "{{:,.2f}}".format(doc.total_deduction) }}}}</b></td></tr>
  </table>
  <h3 style="margin-top:14px">{{{{ _("Net Pay") }}}} / নিট বেতন: {{{{ "{{:,.2f}}".format(doc.net_pay) }}}}</h3>
  <div style="font-size:12px; color:#555">{{{{ _("Computer generated slip; no signature required.") }}}}</div>
</div>
"""


def apply_bd_tax(doc, method=None):
    """Salary Slip validate hook. Sets monthly TDS for Bangladesh SME structures and refreshes net pay."""
    if not (doc.get("salary_structure") or "").startswith(STRUCTURE_PREFIX):
        return
    pf = sum(flt(row.amount) for row in doc.deductions if row.abbr == "PFEMP")
    tds = float(bd.monthly_tds(flt(doc.gross_pay), pf))
    tds_rows = [row for row in doc.deductions if row.abbr == "TDS"]
    if tds_rows:
        for row in tds_rows:
            row.amount = tds
    else:
        # HRMS drops zero-amount structure rows from a slip, so add the TDS row when it is missing.
        doc.append("deductions", {"salary_component": "Income Tax (TDS)", "abbr": "TDS", "amount": tds,
                                  "default_amount": 0})
    if hasattr(doc, "calculate_net_pay"):
        doc.calculate_net_pay()


@frappe.whitelist(methods=["POST"])
def create_festival_bonus(company: str, festival: str, payroll_date: str | None = None,
                          employees: list | None = None) -> dict:
    """Create one Festival Bonus additional salary per eligible employee for a festival.

    ``employees`` limits it to a list (the people on a salary run). Without it, every assigned employee.
    """
    frappe.only_for(["HR Manager", "Payroll Manager", "System Manager"])
    if not frappe.db.exists("Salary Component", FESTIVAL_COMPONENT):
        frappe.throw(_("Run the Bangladesh payroll setup first."))
    day = getdate(payroll_date or nowdate())
    filters = {"company": company, "docstatus": 1}
    if employees is not None:
        filters["employee"] = ["in", list(employees) or [""]]
    assignments = frappe.get_all(
        "Salary Structure Assignment", filters=filters,
        fields=["employee", "base"], limit_page_length=0,
    )
    created, skipped = [], []
    for a in assignments:
        emp = frappe.db.get_value("Employee", a.employee, ["status", "date_of_joining", "employee_name"], as_dict=True)
        if not emp or emp.status != "Active" or not emp.date_of_joining:
            skipped.append(a.employee)
            continue
        months = max(0, (day.year - getdate(emp.date_of_joining).year) * 12
                     + day.month - getdate(emp.date_of_joining).month)
        basic = flt(a.base) * 0.6
        amount = float(bd.festival_bonus(basic, months))
        if amount <= 0:
            skipped.append(a.employee)
            continue
        if frappe.db.exists("Additional Salary", {"employee": a.employee, "salary_component": FESTIVAL_COMPONENT,
                                                  "payroll_date": day, "docstatus": ["!=", 2]}):
            skipped.append(a.employee)
            continue
        doc = frappe.get_doc({
            "doctype": "Additional Salary", "employee": a.employee, "company": company,
            "salary_component": FESTIVAL_COMPONENT, "amount": amount, "payroll_date": day,
            "notes": f"{festival} bonus",
        }).insert(ignore_permissions=True)
        doc.submit()
        created.append(doc.name)
    frappe.db.commit()
    return {"created": len(created), "skipped": len(skipped), "names": created}


@frappe.whitelist()
def bank_sheet(payroll_entry: str) -> str:
    """CSV bank transfer sheet for the submitted slips of a payroll run."""
    if not frappe.has_permission("Payroll Entry", "read", payroll_entry):
        frappe.throw(_("Not permitted to export this payroll run."), frappe.PermissionError)
    slips = frappe.get_all(
        "Salary Slip", filters={"payroll_entry": payroll_entry, "docstatus": 1},
        fields=["employee", "employee_name", "bank_name", "bank_ac_no", "net_pay"],
        order_by="employee asc", limit_page_length=0,
    )
    rows = bd.bank_sheet_rows([dict(s) for s in slips])
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue()
