"""Page 1 (Your company): add people from a CSV file. Template, dry-run check and background import.

The dry run checks every row against this company's offices, departments, job titles, levels and types
of employee. Valid rows are created in batches of 200 by a background job that reports progress.
Rows with errors are skipped, never half-saved.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate

from reckon_hrms import importer
from reckon_hrms.api.home import _company

IMPORT_BATCH = 200
HR_ROLES = ["HR Manager", "HR User", "System Manager"]
MASTERS = {  # field -> (DocType, name field) for the lookups the file refers to
    "branch": ("Branch", "name"),
    "designation": ("Designation", "name"),
    "grade": ("Employee Grade", "name"),
    "employment_type": ("Employment Type", "name"),
}


def _csv_text(file_url: str) -> str:
    if not file_url:
        frappe.throw(_("Choose a CSV file first."))
    doc = frappe.get_doc("File", {"file_url": file_url})
    content = doc.get_content()
    return content.decode("utf-8-sig") if isinstance(content, bytes) else content


def _rows(text: str) -> list[dict]:
    import csv
    import io

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "first_name" not in [f.strip() for f in reader.fieldnames]:
        frappe.throw(_("The file must use the template: the first row needs the column names."))
    rows = []
    for raw in reader:
        rows.append({(k or "").strip(): (v or "").strip() for k, v in raw.items()})
    return rows


def _known(company: str) -> dict[str, set[str]]:
    """Names the file may use. Departments are matched by department name within this company."""
    known = {}
    for field, (doctype, name_field) in MASTERS.items():
        known[field] = set(frappe.get_all(doctype, pluck=name_field, limit_page_length=0))
    known["department"] = set(frappe.get_all(
        "Department", filters={"company": company}, pluck="department_name", limit_page_length=0))
    return known


@frappe.whitelist(methods=["GET"])
def employee_template() -> dict:
    frappe.only_for(HR_ROLES)
    return {"filename": "employee-template.csv", "csv": importer.template_csv()}


@frappe.whitelist(methods=["POST"])
def start_import(file_url: str) -> dict:
    """Dry run: read, check and summarise. Nothing is saved."""
    frappe.only_for(HR_ROLES)
    company = _company()
    rows = _rows(_csv_text(file_url))
    result = importer.check_rows(rows, _known(company))
    return {"read": result["read"], "ready": result["ready"], "to_fix": result["to_fix"],
            "errors": result["errors"]}


@frappe.whitelist(methods=["POST"])
def apply_import(file_url: str) -> dict:
    """Start the real import in the background. Returns a job id to poll."""
    frappe.only_for(HR_ROLES)
    if not frappe.has_permission("Employee", "create"):
        frappe.throw(_("You do not have permission to add employees."), frappe.PermissionError)
    company = _company()
    job = frappe.generate_hash(length=10)
    frappe.cache().set_value(f"reckon_import:{job}", {"state": "queued", "created": 0, "failed": [], "done": 0,
                                                       "total": 0})
    frappe.enqueue("reckon_hrms.api.people.run_import", queue="long", timeout=3600, job_id=job,
                   file_url=file_url, company=company, job=job)
    return {"job": job}


def run_import(file_url, company, job):
    key = f"reckon_import:{job}"
    rows = _rows(_csv_text(file_url))
    result = importer.check_rows(rows, _known(company))
    valid = result["valid"]
    state = {"state": "running", "created": 0, "failed": [], "done": 0, "total": len(valid)}
    for i in range(0, len(valid), IMPORT_BATCH):
        for item in valid[i:i + IMPORT_BATCH]:
            data = item["data"]
            try:
                dept = frappe.db.get_value("Department", {"department_name": data["department"], "company": company}, "name")
                doc = frappe.get_doc({
                    "doctype": "Employee", "company": company, "status": "Active",
                    "first_name": data["first_name"], "last_name": data.get("last_name") or None,
                    "gender": data["gender"].capitalize(),
                    "date_of_birth": getdate(importer.parse_date(data["date_of_birth"])),
                    "date_of_joining": getdate(importer.parse_date(data["date_of_joining"])),
                    "cell_number": data.get("cell_number") or None,
                    "department": dept,
                    "designation": data["designation"],
                    "branch": data.get("branch") or None,
                    "grade": data.get("grade") or None,
                    "employment_type": data.get("employment_type") or None,
                })
                doc.insert(ignore_permissions=True)
                state["created"] += 1
            except Exception as exc:
                state["failed"].append({"row": item["row"], "reason": str(exc)[:160]})
            state["done"] += 1
        frappe.cache().set_value(key, state)
        frappe.publish_realtime("reckon_progress", dict(state, job=job), user=frappe.session.user)
        frappe.db.commit()
    state["state"] = "done"
    frappe.cache().set_value(key, state)
    frappe.publish_realtime("reckon_progress", dict(state, job=job), user=frappe.session.user)


@frappe.whitelist(methods=["GET"])
def get_import_progress(job: str) -> dict:
    frappe.only_for(HR_ROLES)
    return frappe.cache().get_value(f"reckon_import:{job}") or {"state": "unknown"}
