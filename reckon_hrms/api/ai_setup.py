"""The setup interview: questions for every step, a reviewable plan, then one apply.

Ask AI guides the person through the questions and can read free text (for example a list of holidays written in a
sentence). It never writes records itself: ``apply`` rebuilds the plan from the answers and runs fixed, get-or-create
steps for the signed-in company only. Shared masters are only ever added to, never changed.
"""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from reckon_hrms import industry_seed, salary_suggest, setup_plan
from reckon_hrms.api.home import _company

ADMIN_ROLES = ["HR Manager", "System Manager"]
STRUCTURE_COMPONENTS = ("Basic Salary", "House Rent Allowance", "Medical Allowance", "Conveyance Allowance")


def _answers(raw) -> dict:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = {}
    return setup_plan.normalize_answers(raw)


def _segment(key: str):
    return salary_suggest.load_benchmark()["segments"].get(key) if key else None


def country_holiday_count(country: str, year: int):
    """How many public holidays ReckonERP's holiday calendar (the ``holidays`` library) knows for the country that year, else None."""
    code = frappe.db.get_value("Country", country, "code") if country else None
    if not code:
        return None
    try:
        from holidays import country_holidays

        return len(country_holidays(code.upper(), years=year))
    except NotImplementedError:
        return 0
    except Exception:  # noqa: BLE001 - the library is optional
        return None


def _existing(company: str, country: str = "", year: int | None = None) -> dict:
    return {
        "country_holidays": country_holiday_count(country, year or setup_plan.normalize_answers({})["year"]) if country else None,
        "departments": set(frappe.get_all("Department", filters={"company": company}, pluck="department_name")),
        "designations": set(frappe.get_all("Designation", pluck="designation_name")),
        "branches": set(frappe.get_all("Branch", filters={"company": ["in", [company, "", None]]}, pluck="name")),
        "shifts": [{"name": r.name, "start": str(r.start_time), "end": str(r.end_time)}
                   for r in frappe.get_all("Shift Type", filters={"company": company}, fields=["name", "start_time", "end_time"])],
        "leave_policy": frappe.db.get_value("Leave Policy", {"company": company, "docstatus": 1}, "name") or "",
        "rules": _rules_now(company),
        "structures": [r.rsplit(" - " + company, 1)[0] if r.endswith(" - " + company) else r
                       for r in frappe.get_all("Salary Structure", filters={"company": company, "docstatus": 1}, pluck="name")],
    }


@frappe.whitelist(methods=["GET"])
def review_state(studio: str = "hr") -> dict:
    """What the company's setup holds, step by step, with the page to review or edit each one. Read only."""
    frappe.only_for(ADMIN_ROLES + ["Payroll Manager"])
    from reckon_hrms import setup_review

    company = _company()
    mine = ["in", [company, "", None]]
    key = frappe.db.get_value("Company", company, "reckon_industry") or ""
    label = next((s["label"] for s in salary_suggest.segments() if s["key"] == key), "")
    language = frappe.db.get_value("User", frappe.session.user, "language") or ""
    holiday_list = frappe.db.get_value("Holiday List", {"company": company}, "name", order_by="to_date desc") or ""
    weekly, named = [], 0
    if holiday_list:
        rows = frappe.get_all("Holiday", filters={"parent": holiday_list}, fields=["weekly_off", "description"], limit_page_length=0)
        weekly = sorted({r.description for r in rows if r.weekly_off and r.description in setup_plan.WEEKDAYS}, key=setup_plan.WEEKDAYS.index)
        named = sum(1 for r in rows if not r.weekly_off)
    facts = {
        "company": company, "user": frappe.session.user,
        "country": frappe.db.get_value("Company", company, "country") or "",
        "language": setup_plan.LANGUAGES.get(language, language),
        "industry_label": label,
        "branches": frappe.db.count("Branch", {"company": company}),
        "departments": frappe.db.count("Department", {"company": company}),
        "designations": len(frappe.get_all("Designation", filters={"company": mine}, pluck="name")),
        "holiday_list": holiday_list, "weekly_off": weekly, "named_holidays": named,
        "shifts": frappe.db.count("Shift Type", {"company": company}),
        "leave_policies": frappe.db.count("Leave Policy", {"company": company}),
        "structures": frappe.db.count("Salary Structure", {"company": company, "docstatus": 1}),
        "assignments": frappe.db.count("Salary Structure Assignment", {"company": company, "docstatus": 1}),
        "components": len(frappe.get_all("Salary Component", filters={"company": mine}, pluck="name")),
    }
    rows_ = setup_review.rows(facts, studio if studio == "payroll" else "hr")
    return {"company": company, "rows": rows_, "finished": setup_review.finished(rows_)}


def read_current(company: str) -> dict:
    """What the company already has, as interview answers, plus the page that edits each one. Read only."""
    from reckon_hrms import setup_review

    mine = ["in", [company, "", None]]
    answers, links = {}, {}
    country = frappe.db.get_value("Company", company, "country") or ""
    if country:
        answers["country"] = country
    language = frappe.db.get_value("User", frappe.session.user, "language") or ""
    if language in setup_plan.LANGUAGES:
        answers["language"] = language
    branches = frappe.get_all("Branch", filters={"company": company}, pluck="name", order_by="name asc")
    if branches:
        answers["locations"] = ", ".join(branches)
    departments = frappe.get_all("Department", filters={"company": company, "is_group": 0}, pluck="department_name", order_by="department_name asc")
    if departments:
        answers["extra_departments"] = ", ".join(departments)
    titles = frappe.get_all("Designation", filters={"company": company}, pluck="designation_name", order_by="designation_name asc")
    if titles:
        answers["extra_titles"] = ", ".join(titles)
    industry = frappe.db.get_value("Company", company, "reckon_industry") or ""
    holiday_list = frappe.db.get_value("Holiday List", {"company": company}, "name", order_by="to_date desc") or ""
    if holiday_list:
        hl = frappe.db.get_value("Holiday List", holiday_list, ["country"], as_dict=True)
        rows = frappe.get_all("Holiday", filters={"parent": holiday_list}, fields=["weekly_off", "description", "holiday_date"], order_by="holiday_date asc", limit_page_length=0)
        weekly = sorted({r.description for r in rows if r.weekly_off and r.description in setup_plan.WEEKDAYS}, key=setup_plan.WEEKDAYS.index)
        named = [{"date": str(r.holiday_date), "name": r.description} for r in rows if not r.weekly_off]
        answers.update(setup_review.holiday_answers(bool(hl and hl.country), weekly, named))
    abbr = frappe.db.get_value("Company", company, "abbr") or ""
    shift = frappe.db.get_value("Shift Type", {"company": company}, ["name", "start_time", "end_time", "late_entry_grace_period"], as_dict=True)
    if shift:
        answers.update(setup_review.shift_answers(shift.name, shift.start_time, shift.end_time, shift.late_entry_grace_period, abbr))
    policy = frappe.db.get_value("Leave Policy", {"company": company, "docstatus": 1}, "name")
    if policy:
        details = frappe.get_all("Leave Policy Detail", filters={"parent": policy}, fields=["leave_type", "annual_allocation"], limit_page_length=0)
        answers.update(setup_review.leave_answers(details))
    structure = frappe.db.get_value("Salary Structure", {"company": company, "docstatus": 1}, "name", order_by="creation desc")
    if structure:
        earnings = frappe.get_all("Salary Detail", filters={"parent": structure, "parentfield": "earnings"},
                                  fields=["salary_component", "amount", "amount_based_on_formula", "formula"], limit_page_length=0)
        answers.update(setup_review.structure_answers(structure, company, earnings))
        links["structure"] = structure
    rules = _rules_now(company)
    answers.update(rule_marks=str(rules["marks_per_day"]), rule_divisor=str(rules["divisor"]), rule_cap=f"{rules['cap']:g}")
    links.update({"company": company, "user": frappe.session.user, "holiday_list": holiday_list})
    return {"answers": answers, "industry": industry, "links": links, "designations_visible": len(frappe.get_all("Designation", filters={"company": mine}, pluck="name"))}


def _rules_now(company: str) -> dict:
    from reckon_hrms.api.deductions import _policy

    marks, divisor, cap = _policy(company)
    return {"marks_per_day": marks, "divisor": divisor, "cap": float(cap)}


@frappe.whitelist(methods=["GET"])
def payroll_readiness() -> dict:
    """The salary process step by step with its status: what HR Studio already did is only linked, never asked again. Read only."""
    frappe.only_for(ADMIN_ROLES + ["Payroll Manager"])
    from reckon_hrms import setup_review

    company = _company()
    mine = ["in", [company, "", None]]
    active = frappe.db.count("Employee", {"company": company, "status": "Active"})
    assigned = frappe.db.sql(
        "SELECT COUNT(DISTINCT ssa.employee) FROM `tabSalary Structure Assignment` ssa JOIN `tabEmployee` e ON e.name = ssa.employee "
        "WHERE ssa.docstatus = 1 AND e.status = 'Active' AND e.company = %s", (company,))[0][0]
    payable = frappe.db.get_value("Company", company, "default_payroll_payable_account") or ""
    run = frappe.db.get_value("Payroll Entry", {"company": company}, ["name", "docstatus", "creation"], as_dict=True, order_by="creation desc")
    last = None
    if run:
        paid = frappe.db.exists("Salary Slip", {"payroll_entry": run.name, "docstatus": 1, "reckon_payment_entry": ["is", "set"]})
        last = {"name": run.name, "status": "Paid" if paid else ("Draft" if run.docstatus == 0 else "Submitted")}
    facts = {
        "company": company, "employees": frappe.db.count("Employee", {"company": company}),
        "holiday_list": frappe.db.get_value("Holiday List", {"company": company}, "name") or "",
        "shifts": frappe.db.count("Shift Type", {"company": company}),
        "leave_policies": frappe.db.count("Leave Policy", {"company": company}),
        "payable_account": payable,
        "components": len(frappe.get_all("Salary Component", filters={"company": mine}, pluck="name")),
        "structures": frappe.db.count("Salary Structure", {"company": company, "docstatus": 1}),
        "active": active, "assigned": int(assigned or 0), "rules": _rules_now(company), "last_run": last,
    }
    groups = setup_review.payroll_groups(facts)
    pending = setup_review.hr_pending(groups)
    return {"company": company, "groups": groups, "rules": facts["rules"], "hr_pending": pending, "hr_ready": not pending,
            "ready": not pending and all(r["done"] for g in groups for r in g["rows"] if r["key"] in ("payable", "components", "structure", "assignments"))}


@frappe.whitelist(methods=["POST"])
def ensure_payroll_account() -> dict:
    """Give the company the payroll payable account a salary run needs. Safe to repeat."""
    frappe.only_for(ADMIN_ROLES + ["Payroll Manager"])
    from reckon_hrms.payroll import ensure_payroll_payable

    account = ensure_payroll_payable(_company())
    if not account:
        frappe.throw(_("The company has no liabilities account to put it under. Add one in the chart of accounts first."))
    frappe.db.commit()
    return {"account": account}


@frappe.whitelist(methods=["POST"])
def save_payroll_rules(marks_per_day, divisor, cap=0) -> dict:
    """Save the company's late and early deduction rule. Nothing is deducted by saving it."""
    frappe.only_for(ADMIN_ROLES + ["Payroll Manager"])
    clean = setup_plan.normalize_answers({"rule_marks": marks_per_day, "rule_divisor": divisor, "rule_cap": cap})["rules"]
    if not clean or not (clean["marks_per_day"] and clean["divisor"]):
        frappe.throw(_("Give both numbers: marks that equal one day (1 to 31) and the divisor for a day's pay (1 to 31)."))
    return {"saved": _rules(_company(), clean)}


@frappe.whitelist(methods=["GET"])
def current_answers() -> dict:
    """The setup interview pre-filled with what the company already has, and where to edit each part."""
    frappe.only_for(ADMIN_ROLES + ["Payroll Manager"])
    return read_current(_company())


@frappe.whitelist(methods=["GET"])
def questions() -> dict:
    """The interview: every question, the industries to choose from, and the year the holidays are for."""
    frappe.only_for(ADMIN_ROLES + ["Payroll Manager"])
    company = _company()
    return {"questions": setup_plan.QUESTIONS, "industries": salary_suggest.segments(), "weekdays": list(setup_plan.WEEKDAYS),
            "countries": frappe.get_all("Country", pluck="name", order_by="name asc", limit_page_length=0),
            "languages": setup_plan.LANGUAGES, "weekly_off_by_country": setup_plan.WEEKLY_OFF_BY_COUNTRY,
            "default_weekly_off": setup_plan.DEFAULT_WEEKLY_OFF,
            "current_country": frappe.db.get_value("Company", company, "country") or "",
            "current_language": frappe.db.get_value("User", frappe.session.user, "language") or "",
            "leave_types": [label for _key, label in setup_plan.LEAVE_QUESTIONS], "year": setup_plan.normalize_answers({})["year"],
            "company": company}


def _ai_ready():
    try:
        from reckon_aura_theme import api as aura

        settings = aura._settings()
        return (aura, settings) if aura._ai_ready(settings) else None
    except Exception:  # noqa: BLE001 - AI is optional
        return None


def _ai_json(prompt: str, user: str, max_tokens: int = 700):
    """One strict-JSON question to the company's AI, or None when AI is off or the reply cannot be read."""
    ready = _ai_ready()
    if not ready:
        return None
    aura, settings = ready
    try:
        raw = aura._complete(settings, prompt, user, max_tokens=max_tokens, quiet=True)
        text = (raw or "").strip().strip("`")
        start = min([i for i in (text.find("["), text.find("{")) if i != -1] or [-1])
        end = max(text.rfind("]"), text.rfind("}"))
        return json.loads(text[start:end + 1]) if start != -1 and end > start else None
    except Exception:  # noqa: BLE001 - a failing provider must not stop the setup
        return None


def _ai_text(system: str, user: str, max_tokens: int = 400, timeout: int = 30):
    """One plain-text answer from the company's AI, or None when AI is off, over its daily limit, or fails."""
    ready = _ai_ready()
    if not ready:
        return None
    aura, settings = ready
    try:
        return (aura._complete(settings, system, user, max_tokens=max_tokens, quiet=True, timeout=timeout) or "").strip() or None
    except Exception:  # noqa: BLE001 - AI is optional; the plain reader carries on
        return None


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=30, seconds=60 * 60)
def prepare(answers) -> dict:
    """Read the answers, let Ask AI read any holiday text it can, and return the plan to review. Changes nothing."""
    frappe.only_for(ADMIN_ROLES)
    return build_reviewed_plan(answers)


def build_reviewed_plan(answers) -> dict:
    company = _company()
    clean = _answers(answers)
    ai_used = False
    if clean["holidays_unread"]:
        # Free-text holidays: ask the AI to turn them into dates, then keep only well-formed ones in this year.
        rows = _ai_json(
            "Turn the text into a JSON array of public holidays, each {\"date\": \"YYYY-MM-DD\", \"name\": \"...\"}. "
            f"Use the year {clean['year']} when the year is missing. Return only the array. Never invent a holiday that is not in the text.",
            "\n".join(clean["holidays_unread"]))
        lines = setup_plan.parse_ai_holidays(rows, clean["year"])
        if lines:
            ai_used = True
            merged = list(clean["holidays"]) + setup_plan.parse_holidays("\n".join(lines), clean["year"])[0]
            seen, holidays = set(), []
            for h in sorted(merged, key=lambda x: x["date"]):
                if h["date"] not in seen:
                    seen.add(h["date"])
                    holidays.append(h)
            clean["holidays"], clean["holidays_unread"] = holidays[:setup_plan.MAX_HOLIDAYS], []
    plan = setup_plan.build_plan(clean, _segment(clean["industry"]), company, _existing(company, clean["country"], clean["year"]))
    plan["answers"] = {k: clean[k] for k in ("industry", "year")}
    plan["ai_used"] = ai_used
    return plan


# ---- apply: fixed, company-scoped, get-or-create steps

def _holiday_list(company: str, answers: dict) -> str:
    year = answers["year"]
    start, end = f"{year}-01-01", f"{year}-12-31"
    name = frappe.db.get_value("Holiday List", {"company": company, "from_date": ["<=", start], "to_date": [">=", end]}, "name")
    if name:
        doc = frappe.get_doc("Holiday List", name)
    else:
        doc = frappe.get_doc({"doctype": "Holiday List", "holiday_list_name": f"Holidays {year} - {company}"[:140], "company": company,
                              "from_date": start, "to_date": end})
    from datetime import date, timedelta

    chosen = set(answers["weekly_off"])
    doc.set("holidays", [r for r in doc.get("holidays") or [] if not r.weekly_off or r.description in chosen])
    have = {str(r.holiday_date) for r in doc.get("holidays") or []}
    day = date(year, 1, 1)
    while day.year == year:
        weekday = day.strftime("%A")
        if weekday in chosen and day.isoformat() not in have:
            doc.append("holidays", {"holiday_date": day.isoformat(), "description": weekday, "weekly_off": 1})
            have.add(day.isoformat())
        day += timedelta(days=1)
    if answers.get("holidays_country") and answers.get("country"):
        # ReckonERP's own feature: pick the country on the Holiday List and "Get holidays" fills in its public holidays.
        code = frappe.db.get_value("Country", answers["country"], "code")
        if code:
            doc.country = code.upper()
            try:
                doc.get_local_holidays()
            except NotImplementedError:
                frappe.msgprint(_("ReckonERP has no holiday calendar for {0}.").format(answers["country"]))
    have = {str(r.holiday_date) for r in doc.get("holidays") or []}
    for h in answers["holidays"]:
        if h["date"] not in have:
            doc.append("holidays", {"holiday_date": h["date"], "description": h["name"]})
            have.add(h["date"])
    if answers["weekly_off"]:
        doc.weekly_off = answers["weekly_off"][0]
    doc.flags.ignore_permissions = True
    if doc.get("name"):
        doc.save()
    else:
        doc.insert()
    if not frappe.db.get_value("Company", company, "default_holiday_list"):
        frappe.db.set_value("Company", company, "default_holiday_list", doc.name)
    return doc.name


def _shift(company: str, shift: dict) -> str:
    abbr = frappe.db.get_value("Company", company, "abbr") or ""
    name = f"{shift['name']} - {abbr}"[:140] if abbr else shift["name"]
    if frappe.db.exists("Shift Type", name) or frappe.db.exists(
        "Shift Type", {"company": company, "start_time": shift["start"], "end_time": shift["end"]}
    ):
        return "Already there, left as it is"
    values = {"doctype": "Shift Type", "name": name, "company": company, "start_time": shift["start"], "end_time": shift["end"]}
    if shift["grace"]:
        values.update(enable_late_entry_marking=1, late_entry_grace_period=shift["grace"])
    frappe.get_doc(values).insert(ignore_permissions=True)
    return "created"


def _leave_policy(company: str, leave: dict) -> str:
    title = f"{company} Leave Policy"[:140]
    if frappe.db.exists("Leave Policy", {"title": title}) or frappe.db.exists("Leave Policy", {"company": company, "docstatus": 1}):
        return "Already there, left as it is"
    for leave_type in leave:
        industry_seed._leave_type(leave_type)
    doc = frappe.get_doc({"doctype": "Leave Policy", "title": title,
                          "leave_policy_details": [{"leave_type": k, "annual_allocation": v} for k, v in leave.items()]})
    doc.insert(ignore_permissions=True)
    doc.submit()
    return "created"


def _structure(company: str, spec: dict) -> str:
    name = f"{spec['name']} - {company}"[:140]
    if frappe.db.exists("Salary Structure", name):
        return "Already there, left as it is"
    for component in STRUCTURE_COMPONENTS:
        industry_seed._component(component)
        industry_seed._ensure_component_account(company, component)
    abbr = {"Basic Salary": "BASIC", "House Rent Allowance": "HRA", "Medical Allowance": "MED", "Conveyance Allowance": "CONV"}
    rows = [{"salary_component": "Basic Salary", "abbr": abbr["Basic Salary"], "amount_based_on_formula": 1,
             "formula": f"base * {spec['basic_pct'] / 100:g}", "depends_on_payment_days": 1}]
    if spec["hra_pct"]:
        rows.append({"salary_component": "House Rent Allowance", "abbr": "HRA", "amount_based_on_formula": 1,
                     "formula": f"base * {spec['hra_pct'] / 100:g}", "depends_on_payment_days": 0})
    if spec["medical"]:
        rows.append({"salary_component": "Medical Allowance", "abbr": "MED", "amount": spec["medical"]})
    if spec["conveyance"]:
        rows.append({"salary_component": "Conveyance Allowance", "abbr": "CONV", "amount": spec["conveyance"]})
    doc = frappe.get_doc({"doctype": "Salary Structure", "name": name, "company": company, "is_active": "Yes", "payroll_frequency": "Monthly",
                          "currency": frappe.db.get_value("Company", company, "default_currency"), "earnings": rows})
    doc.insert(ignore_permissions=True)
    doc.submit()
    return "created"


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=20, seconds=60 * 60)
def apply(answers) -> dict:
    """Run the plan the person reviewed. Rebuilt from the answers here, so only the fixed steps above can run."""
    frappe.only_for(ADMIN_ROLES)
    return run_setup(answers)


def run_setup(answers) -> dict:
    if not frappe.has_permission("Company", "write"):
        frappe.throw(_("You do not have permission to change this company's setup."), frappe.PermissionError)
    company = _company()
    clean = _answers(answers)
    plan = setup_plan.build_plan(clean, _segment(clean["industry"]), company, _existing(company, clean["country"], clean["year"]))
    results = []

    def run(key, label, fn):
        step = next((s for s in plan["steps"] if s["key"] == key), None)
        if not step or step["status"] != "ready":
            results.append({"key": key, "label": label, "result": "skipped", "message": (step or {}).get("note") or "Nothing to do."})
            return
        savepoint = f"ai_setup_{key}"
        frappe.db.savepoint(savepoint)
        try:
            outcome = fn()
            results.append({"key": key, "label": label, "result": "done", "message": outcome if isinstance(outcome, str) else ""})
        except Exception as exc:  # noqa: BLE001 - one failed step must not stop the others
            frappe.db.rollback(save_point=savepoint)
            frappe.log_error(frappe.get_traceback(), f"Setup interview {key}")
            results.append({"key": key, "label": label, "result": "failed", "message": str(exc)[:200]})

    run("country", "Country", lambda: _country(company, clean["country"]))
    run("language", "Language", lambda: _language(clean["language"]))
    run("locations", "Locations", lambda: _locations(clean["locations"]))
    run("industry", "Industry starter items", lambda: _fmt_industry(industry_seed.apply_segment(company, clean["industry"])))
    run("departments", "Departments", lambda: f"{sum(industry_seed._department(company, n) == 'created' for n in clean['extra_departments'])} added")
    run("titles", "Job titles", lambda: f"{sum(industry_seed._designation(n) == 'created' for n in clean['extra_titles'])} added")
    run("holidays", "Holiday calendar", lambda: f"Saved as {_holiday_list(company, clean)}")
    run("shift", "Working hours", lambda: _shift(company, clean["shift"]))
    run("leave", "Leave policy", lambda: _leave_policy(company, clean["leave"]))
    run("structure", "Salary structure", lambda: _structure(company, clean["structure"]))
    run("rules", "Attendance deduction rule", lambda: _rules(company, clean["rules"]))
    frappe.db.commit()
    return {"company": company, "results": results, "done": sum(r["result"] == "done" for r in results),
            "failed": sum(r["result"] == "failed" for r in results)}


def _rules(company: str, rules: dict) -> str:
    meta = frappe.get_meta("Company")
    if not meta.has_field("reckon_marks_per_day"):
        frappe.throw(_("The attendance deduction fields are not installed on this site yet."))
    frappe.db.set_value("Company", company, {"reckon_marks_per_day": rules["marks_per_day"], "reckon_deduction_divisor": rules["divisor"],
                                             "reckon_deduction_cap": rules["cap"]})
    return "Saved"


def _country(company: str, country: str) -> str:
    if not frappe.db.exists("Country", country):
        frappe.throw(_("Unknown country: {0}").format(country))
    if frappe.db.get_value("Company", company, "country"):
        return "The company already has a country, so it was left as it is"
    frappe.db.set_value("Company", company, "country", country)
    return f"Company country set to {country}"


def _language(language: str) -> str:
    if frappe.session.user in ("Administrator", "Guest"):
        return "Skipped for this account"
    frappe.db.set_value("User", frappe.session.user, "language", language)
    return f"Your language is now {setup_plan.LANGUAGES[language]}. It applies after you reload the page"


def _locations(names: list[str]) -> str:
    made, taken = 0, []
    for name in names:
        if frappe.db.exists("Branch", name):
            taken.append(name)
            continue
        frappe.get_doc({"doctype": "Branch", "branch": name}).insert(ignore_permissions=True)
        made += 1
    return f"{made} added" + (f"; already there: {', '.join(taken)}" if taken else "")


def _fmt_industry(result: dict) -> str:
    c = result["created"]
    return f"Added {c['designations']} job titles, {c['departments']} departments, {c['components']} pay items, {c['leave_types']} leave types"
