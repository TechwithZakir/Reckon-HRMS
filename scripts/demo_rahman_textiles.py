"""Demo data for the user manual: Rahman Textiles Ltd., one month of payroll, hiring and one exit.

Run once on a site with Reckon HRMS installed:
    bench --site <site> console < scripts/demo_rahman_textiles.py

Creates only what is missing, so a repeat run adds nothing twice. Every name is a realistic
Bangladeshi name; no test labels.
"""

import frappe
from frappe.utils import flt

from reckon_hrms import industry_seed, payroll
from reckon_hrms import seed as hrms_seed
from reckon_hrms.api import payroll_run as pr
from reckon_hrms.api import deductions as ded

CO = "Rahman Textiles Ltd."
ABBR = "RTXL"
SEGMENT = "manufacturing_rmg_textile"
MONTH = "2026-11"
PAY_DATE = "2026-11-30"
JOIN = "2024-07-01"

BRANCHES = {
    "Gazipur Factory": (23.9999, 90.4203),
    "Dhaka Head Office": (23.7396, 90.3965),
}

# (first name, last name, gender, date of birth, designation, branch, department, base salary)
PEOPLE = [
    ("Rafiqul", "Islam", "Male", "1978-03-12", "Factory Manager", "Gazipur Factory", "Production", 115000),
    ("Nasrin", "Akter", "Female", "1986-09-04", "HR Manager", "Dhaka Head Office", "Human Resources", 95000),
    ("Shahidul", "Haque", "Male", "1984-01-20", "Production Supervisor", "Gazipur Factory", "Production", 40000),
    ("Fatema", "Khatun", "Female", "1990-06-15", "Quality / QA Executive", "Gazipur Factory", "Quality", 37500),
    ("Jewel", "Rana", "Male", "1997-11-02", "Machine Operator (skilled)", "Gazipur Factory", "Production", 20000),
    ("Sumaiya", "Hossain", "Female", "1999-04-27", "Machine Operator (skilled)", "Gazipur Factory", "Production", 20000),
    ("Abdul", "Karim", "Male", "1981-07-08", "Accountant / Finance Executive", "Dhaka Head Office", "Accounts and Finance", 47500),
    ("Tasnim", "Jahan", "Female", "1995-02-18", "Sales Executive", "Dhaka Head Office", "Sales and Distribution", 29500),
    ("Mizanur", "Rahman", "Male", "1988-12-30", "Store Keeper", "Gazipur Factory", "Store", 30000),
    ("Shirin", "Sultana", "Female", "1992-05-22", "Office Assistant", "Dhaka Head Office", "Human Resources", 20000),
]

# Attendance: late and early marks per person (day offsets from 2 November 2026).
MARKS = {"Jewel": ("late", [0, 1, 2]), "Sumaiya": ("late", [3]), "Rafiqul": ("early", [1, 4])}
WORKDAYS = ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"]


def log(*args):
    print("DEMO", *args)


def ensure(doctype, filters, values):
    name = frappe.db.get_value(doctype, filters, "name")
    if name:
        return name
    doc = frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)
    return doc.name


def company():
    if not frappe.db.exists("Company", CO):
        frappe.get_doc({"doctype": "Company", "company_name": CO, "abbr": ABBR, "default_currency": "BDT",
                        "country": "Bangladesh"}).insert(ignore_permissions=True)
        log("company created")
    frappe.db.commit()
    industry_seed.apply_segment(CO, SEGMENT)
    hrms_seed.ensure_company_defaults(CO)
    log("setup", payroll.setup_bd_payroll(CO))
    frappe.db.commit()


def branches_and_locations():
    for branch, (lat, lon) in BRANCHES.items():
        ensure("Branch", {"name": branch}, {"branch": branch})
        ensure("HRMS Office Location", {"company": CO, "branch": branch},
               {"company": CO, "branch": branch, "latitude": lat, "longitude": lon, "radius_m": 150})
    frappe.db.commit()
    log("branches and office locations ready")


def designations_and_departments():
    for _f, _l, _g, _d, desig, _b, dept, _base in PEOPLE:
        if not frappe.db.exists("Designation", desig):
            frappe.get_doc({"doctype": "Designation", "designation_name": desig}).insert(ignore_permissions=True)
        ensure("Department", {"department_name": dept, "company": CO},
               {"department_name": dept, "company": CO})
    frappe.db.commit()


def employees():
    names = {}
    for first, last, gender, dob, desig, branch, dept, base in PEOPLE:
        dept_name = frappe.db.get_value("Department", {"department_name": dept, "company": CO}, "name")
        emp = frappe.db.get_value("Employee", {"first_name": first, "last_name": last, "company": CO}, "name")
        if not emp:
            doc = frappe.get_doc({
                "doctype": "Employee", "first_name": first, "last_name": last, "company": CO,
                "gender": gender, "date_of_birth": dob, "date_of_joining": JOIN, "status": "Active",
                "designation": desig, "branch": branch, "department": dept_name,
                "bank_name": "Dutch-Bangla Bank", "bank_ac_no": f"{1000 + len(names):010d}",
                "cell_number": f"0171{len(names):07d}",
            }).insert(ignore_permissions=True)
            emp = doc.name
        names[first] = (emp, base)
    frappe.db.commit()
    log("employees", len(names))
    return names


def assignments(names):
    structure = payroll.structure_name(CO)
    for first, (emp, base) in names.items():
        if not frappe.db.exists("Salary Structure Assignment", {"employee": emp, "docstatus": 1,
                                                                 "from_date": "2026-11-01"}):
            ssa = frappe.get_doc({"doctype": "Salary Structure Assignment", "employee": emp, "company": CO,
                                  "salary_structure": structure, "from_date": "2026-11-01", "base": base,
                                  "currency": "BDT"}).insert(ignore_permissions=True)
            ssa.submit()
    frappe.db.commit()
    log("assignments done")


def attendance(names):
    for first, (emp, _base) in names.items():
        for i, day in enumerate(WORKDAYS):
            if frappe.db.exists("Attendance", {"employee": emp, "attendance_date": day, "docstatus": 1}):
                continue
            kind, days = MARKS.get(first, (None, []))
            values = {"doctype": "Attendance", "employee": emp, "attendance_date": day, "status": "Present",
                      "company": CO}
            if kind == "late" and i in days:
                values["late_entry"] = 1
            if kind == "early" and i in days:
                values["early_exit"] = 1
            doc = frappe.get_doc(values).insert(ignore_permissions=True)
            doc.submit()
    frappe.db.commit()
    log("attendance done")


def payroll_month(names):
    pr._company = lambda: CO
    run = pr.start_run(MONTH, PAY_DATE)["name"]
    pr.fetch_employees(run)
    frappe.db.commit()
    preview = ded._rows(run)[1]
    to_apply = [r["employee"] for r in preview if r["days"] > 0]
    log("late deduction rows", [(r["employee_name"], r["marks"], r["days"], r["amount"]) for r in preview])
    if to_apply:
        ded.apply_attendance_deductions(run, to_apply)
    pr.run_create_slips(run, "demo-slips")
    frappe.db.commit()
    pr.run_approve(run, "demo-approve")
    frappe.db.commit()
    cash = frappe.db.get_value("Account", {"company": CO, "account_type": "Cash", "is_group": 0}, "name")
    pay = pr.record_payment(run, cash, "DEMO-NOV-2026", PAY_DATE)
    frappe.db.commit()
    log("payroll", run, pay)
    return run


def hiring():
    desig = "Quality / QA Executive"
    opening = ensure("Job Opening", {"job_title": "QA Executive - Gazipur", "company": CO},
                     {"job_title": "QA Executive - Gazipur", "company": CO, "designation": desig,
                      "status": "Open", "posting_date": "2026-10-15"})
    applicant = ensure("Job Applicant", {"applicant_name": "Mehedi Hasan", "job_title": opening},
                       {"applicant_name": "Mehedi Hasan", "job_title": opening, "email_id": "mehedi.hasan@example.com",
                        "phone_number": "01715000123", "status": "Accepted"})
    ensure("Job Offer", {"job_applicant": applicant},
           {"job_applicant": applicant, "designation": desig, "company": CO, "offer_date": "2026-10-25",
            "status": "Accepted"})
    frappe.db.commit()
    log("hiring records ready")


def exit_record(names):
    emp = names["Shirin"][0]
    if frappe.db.get_value("Employee", emp, "status") == "Active":
        frappe.db.set_value("Employee", emp, {"status": "Left", "relieving_date": "2026-11-08"})
    frappe.db.commit()
    log("exit recorded for", emp)


frappe.set_user("Administrator")
company()
branches_and_locations()
designations_and_departments()
people = employees()
assignments(people)
attendance(people)
payroll_month(people)
hiring()
exit_record(people)
log("done")
