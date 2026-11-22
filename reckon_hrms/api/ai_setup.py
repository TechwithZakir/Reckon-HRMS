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
    """How many public holidays ERPNext's holiday calendar (the ``holidays`` library) knows for the country that year, else None."""
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
    }


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
        # ERPNext's own feature: pick the country on the Holiday List and "Get holidays" fills in its public holidays.
        code = frappe.db.get_value("Country", answers["country"], "code")
        if code:
            doc.country = code.upper()
            try:
                doc.get_local_holidays()
            except NotImplementedError:
                frappe.msgprint(_("ERPNext has no holiday calendar for {0}.").format(answers["country"]))
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
    if frappe.db.exists("Shift Type", name):
        return "exists"
    values = {"doctype": "Shift Type", "name": name, "company": company, "start_time": shift["start"], "end_time": shift["end"]}
    if shift["grace"]:
        values.update(enable_late_entry_marking=1, late_entry_grace_period=shift["grace"])
    frappe.get_doc(values).insert(ignore_permissions=True)
    return "created"


def _leave_policy(company: str, leave: dict) -> str:
    title = f"{company} Leave Policy"[:140]
    if frappe.db.exists("Leave Policy", {"title": title}):
        return "exists"
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
        return "exists"
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
    frappe.db.commit()
    return {"company": company, "results": results, "done": sum(r["result"] == "done" for r in results),
            "failed": sum(r["result"] == "failed" for r in results)}


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
