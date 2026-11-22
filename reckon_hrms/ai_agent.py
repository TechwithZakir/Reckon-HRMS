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

    cur = ai_setup.read_current(company)
    return {
        "company": company,
        "countries": frappe.get_all("Country", pluck="name", order_by="name asc", limit_page_length=0),
        "industries": salary_suggest.segments(),
        "year": setup_plan.normalize_answers({})["year"],
        "current_country": frappe.db.get_value("Company", company, "country") or "",
        "country_holiday_count": lambda country: ai_setup.country_holiday_count(country, setup_plan.normalize_answers({})["year"]),
        **{"current": cur["answers"], "current_industry": cur["industry"]},
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
