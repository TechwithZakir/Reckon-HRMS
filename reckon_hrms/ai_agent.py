"""Ask Aura AI's setup agent for Reckon HRMS: the chat asks the setup questions and then sets everything up.

Registered in hooks as ``aura_agents``. Aura passes each chat message and the agent's own state; the state lives in the
browser, so every turn is cleaned again and ``run_setup`` rebuilds the plan from the answers before it runs anything.
"""

from __future__ import annotations

import frappe

from reckon_hrms import salary_suggest, setup_chat, setup_plan
from reckon_hrms.api import ai_setup
from reckon_hrms.api.home import _company

ROLES = ("HR Manager", "System Manager")


def _env(company: str) -> dict:
    def build_plan(answers):
        clean = ai_setup._answers(answers)
        plan = setup_plan.build_plan(clean, ai_setup._segment(clean["industry"]), company, ai_setup._existing(company, clean["country"], clean["year"]))
        return plan

    def ai_holidays(text):
        rows = ai_setup._ai_json(
            "Turn the text into a JSON array of public holidays, each {\"date\": \"YYYY-MM-DD\", \"name\": \"...\"}. "
            "Return only the array. Never invent a holiday that is not in the text.", text)
        return setup_plan.parse_ai_holidays(rows, setup_plan.normalize_answers({})["year"])

    def ai_text(key, text, fmt):
        system = ("Rewrite the user's reply to a setup question into this exact short form: " + fmt + ". Return only the rewritten text, "
                  "with no explanation. If the reply does not state the information, return exactly NONE. Never add a value the reply does not state.")
        out = ai_setup._ai_text(system, text[:1500], 200)
        return None if not out or out.strip().upper().startswith("NONE") else out.strip("`").strip()

    def ai_answer(question, step_title):
        ready = ai_setup._ai_ready()
        if not ready:
            return None
        aura, settings = ready
        try:
            aura._consume_daily_ask_quota(settings)
            guides = "".join(f"\n\n<support_guide module=\"{g['id']}\">\n{c}\n</support_guide>"
                             for g, c in aura._get_support_skills(question, "reckon-hrms/reckon-hrms-hr-studio"))
            system = (aura._ask_system_prompt(settings) + "\n\nThe person is in the middle of the ReckonERP HR setup interview, on the step "
                      f"'{step_title}'. Answer their question in at most four short sentences, in plain words. Do not ask a question and do not say "
                      "you changed anything: the interview carries on by itself afterwards.")
            return (aura._complete(settings, system, f"Question: {question[:600]}{guides}", max_tokens=400, quiet=True, timeout=40) or "").strip() or None
        except Exception:  # noqa: BLE001 - a failing AI must not stop the interview
            return None

    cur = ai_setup.read_current(company)
    from reckon_hrms.setup_review import hr_pending

    readiness = ai_setup.payroll_readiness()
    return {
        "hr_pending": [r["label"] for r in hr_pending(readiness["groups"])],
        "company": company,
        "countries": frappe.get_all("Country", pluck="name", order_by="name asc", limit_page_length=0),
        "industries": salary_suggest.segments(),
        "year": setup_plan.normalize_answers({})["year"],
        "current_country": frappe.db.get_value("Company", company, "country") or "",
        "country_holiday_count": lambda country: ai_setup.country_holiday_count(country, setup_plan.normalize_answers({})["year"]),
        **{"current": cur["answers"], "current_industry": cur["industry"]},
        "ai_text": ai_text,
        "ai_answer": ai_answer,
        "build_plan": build_plan,
        "apply": ai_setup.run_setup,
        "ai_holidays": ai_holidays,
    }


def intent(question: str, route: str = "") -> str | None:
    """Aura asks every plain question on an HR page: a setup request starts the agent instead of a text suggestion."""
    if not set(ROLES) & set(frappe.get_roles()):
        return None
    return setup_chat.intent(question, route)


def chat(message: str, state=None) -> dict:
    """One turn of the setup chat: ``{"reply", "state", "replies", "done"}``."""
    if not set(ROLES) & set(frappe.get_roles()):
        return {"reply": "Setting up HR needs the HR Manager role. Ask your administrator.", "state": None, "replies": [], "done": True}
    return setup_chat.turn(message, state, _env(_company()))
