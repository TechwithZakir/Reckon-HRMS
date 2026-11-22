"""The setup agent inside Ask Aura AI: it asks the interview questions in the chat, reads each reply, then sets everything up.

Pure state machine (no Frappe): ``turn(message, state, env)`` returns the reply, the new state and quick replies.
``env`` supplies what only the site knows: countries, industries, the plan builder, the apply step and an optional AI
reader for free text. Nothing is created until the person confirms at the end, and a reply that cannot be read is asked
again, never guessed.
"""

from __future__ import annotations

import difflib
import re

from reckon_hrms import setup_plan as sp

STEPS = ["country", "language", "locations", "industry", "extra_departments", "extra_titles", "weekly_off", "holidays",
         "shift", "leave", "structure"]
TITLES = {"country": "Country", "language": "Language", "locations": "Locations", "industry": "Industry",
          "extra_departments": "Departments", "extra_titles": "Job titles", "weekly_off": "Weekly off", "holidays": "Public holidays",
          "shift": "Working hours", "leave": "Leave days", "structure": "Salary structure"}
# The answer keys each step owns: skipping or redoing a step clears them, so a half-answer never lingers in the plan.
STEP_KEYS = {
    "country": ("country",), "language": ("language",), "locations": ("locations",), "industry": ("industry",),
    "extra_departments": ("extra_departments",), "extra_titles": ("extra_titles",), "weekly_off": ("weekly_off",),
    "holidays": ("holidays", "holidays_country"), "shift": ("shift_name", "shift_start", "shift_end", "late_grace"),
    "leave": ("leave_casual", "leave_sick", "leave_earned", "leave_maternity"),
    "structure": ("structure_name", "basic_pct", "hra_pct", "medical_amount", "conveyance_amount"),
}
# A plan step belongs to the question that fixes it.
PLAN_STEP_TO_QUESTION = {"departments": "extra_departments", "titles": "extra_titles"}
# Words that ask for a page, and the menu name Aura turns into a link.
PAGE_LINKS = (("holiday", "Holiday List"), ("employee", "Employee"), ("department", "Department"), ("branch", "Branch"), ("location", "Branch"),
              ("leave", "Leave Type"), ("shift", "Shift Type"), ("salary structure", "Salary Structure"), ("payroll", "Payroll Studio"),
              ("hr studio", "HR Studio"))
CHANGE_WORDS = re.compile(r"\b(change|edit|redo|fix|update|correct|go to|back to)\b", re.IGNORECASE)
SKIP = {"skip", "none", "no", "nothing", "n/a", "na", "pass", "না", "skip this"}
YES = {"yes", "y", "ok", "okay", "confirm", "go", "go ahead", "set up", "set everything up", "yes, set everything up", "do it", "হ্যাঁ", "yes please"}
ALIASES = {"bd": "Bangladesh", "uk": "United Kingdom", "usa": "United States", "us": "United States", "uae": "United Arab Emirates"}
DAY_WORDS = {d.lower(): d for d in sp.WEEKDAYS}
DAY_WORDS.update({d[:3].lower(): d for d in sp.WEEKDAYS})
LEAVE_WORDS = (("leave_casual", r"casual"), ("leave_sick", r"sick"), ("leave_earned", r"earned|annual"), ("leave_maternity", r"maternity"))
NUM = r"(\d+(?:\.\d+)?)"


def _clean_state(state) -> dict:
    state = state if isinstance(state, dict) else {}
    answers = state.get("answers") if isinstance(state.get("answers"), dict) else {}
    keep = {}
    for key, value in answers.items():
        if isinstance(key, str) and len(key) < 40 and isinstance(value, (str, int, float, list)):
            keep[key] = value if not isinstance(value, list) else [str(v)[:40] for v in value[:10]]
    idx = state.get("idx") if isinstance(state.get("idx"), int) else 0
    phase = state.get("phase") if state.get("phase") in ("ask", "review", "done") else "ask"
    return {"idx": max(0, min(idx, len(STEPS))), "answers": keep, "phase": phase, "started": bool(state.get("started")),
            "fixing": bool(state.get("fixing"))}


def _pick_country(text: str, countries: list[str]):
    word = text.strip().strip(".").casefold()
    if word in ALIASES and ALIASES[word] in countries:
        return ALIASES[word], None
    exact = [c for c in countries if c.casefold() == word]
    if exact:
        return exact[0], None
    starts = [c for c in countries if c.casefold().startswith(word)] if len(word) >= 3 else []
    if len(starts) == 1:
        return starts[0], None
    close = difflib.get_close_matches(text.strip().title(), countries, n=3, cutoff=0.75)
    return None, ("I could not find that country." + (f" Did you mean {', '.join(close)}?" if close else " Please type the country's full name."))


# Words people use for what their company does, mapped to the industry keys of the benchmark.
INDUSTRY_WORDS = {
    "it_software": ("software", "it company", "tech", "app development", "web development", "saas", "digital agency"),
    "manufacturing_rmg_textile": ("garment", "rmg", "textile", "factory", "knit", "apparel", "spinning", "weaving", "manufactur"),
    "construction_engineering": ("construction", "contractor", "civil", "engineering firm", "real estate developer", "builder"),
    "corporate_finance": ("bank", "finance", "accounting", "audit", "insurance", "corporate", "consult"),
    "sales_marketing": ("marketing", "advertis", "sales agency", "promotion"),
    "pharmaceuticals": ("pharma", "medicine", "drug"),
    "trading_distribution": ("trading", "distribut", "wholesale", "importer", "dealer", "fmcg"),
    "healthcare": ("hospital", "clinic", "diagnostic", "healthcare", "medical centre", "nursing"),
    "education_ngo_services": ("school", "college", "university", "ngo", "nonprofit", "training", "education", "service"),
    "retail_logistics": ("retail", "shop", "store", "supermarket", "logistics", "courier", "delivery", "transport"),
}
SETUP_INTENT = re.compile(r"(set ?up|configure|guide me|get started|onboard|which industry|choose (?:my |an |the )?industry|pre-?load|what will .* load)", re.IGNORECASE)


def intent(question: str, route: str) -> str | None:
    """The first chat message for the setup agent when a plain question on an HR page is really a request to set up, else None."""
    if "reckon-hrms" not in (route or "").casefold() and "hr-studio" not in (route or "").casefold():
        return None
    text = (question or "")[:600]
    if not SETUP_INTENT.search(text):
        return None
    return "start industry" if re.search(r"industry|what does my company do", text, re.IGNORECASE) else "start"


def _pick_industry(text: str, industries: list[dict]):
    word = text.strip().casefold()
    if word.isdigit() and 1 <= int(word) <= len(industries):
        return industries[int(word) - 1]["key"], None
    for item in industries:
        if word in (item["key"].casefold(), item["label"].casefold()):
            return item["key"], None
    hits = [i for i in industries if word and (word in i["label"].casefold() or any(w in i["label"].casefold() for w in re.findall(r"[a-z]{4,}", word)))]
    if len(hits) == 1:
        return hits[0]["key"], None
    # A description of the business ("we make garments", "a small clinic") picks the industry whose words it uses most.
    scored = sorted(((sum(w in word for w in words), key) for key, words in INDUSTRY_WORDS.items() if any(i["key"] == key for i in industries)), reverse=True)
    if scored and scored[0][0] and (len(scored) < 2 or scored[0][0] > scored[1][0]):
        return scored[0][1], None
    return None, "I could not tell which industry fits."


def _parse_days(text: str, country: str):
    low = text.casefold()
    if re.search(r"\b(usual|default|same|normal|standard)\b", low):
        return sp.suggest_weekly_off(country), None
    found = []
    for word in re.findall(r"[a-z]+", low):
        day = DAY_WORDS.get(word)
        if day and day not in found:
            found.append(day)
    return (found, None) if found else (None, "Tell me the weekly off days, for example: Friday and Saturday. Or say \"usual\" for the usual days.")


def _parse_shift(text: str):
    times = re.findall(r"([01]?\d|2[0-3]):([0-5]\d)", text)
    if len(times) < 2:
        return None, "Give the shift name and its start and end time, for example: General Shift 09:00 to 17:30, grace 10 minutes."
    spans = list(re.finditer(r"(?:[01]?\d|2[0-3]):[0-5]\d", text))
    name = re.sub(r"\b(from|at|starts?|between|is)\b", " ", text[:spans[0].start()], flags=re.IGNORECASE).strip(" ,:-") or "General Shift"
    grace = re.search(r"grace\D{0,12}" + NUM, text, re.IGNORECASE) or re.search(NUM + r"\s*min", text, re.IGNORECASE)
    out = {"shift_name": name[:60], "shift_start": spans[0].group(0), "shift_end": spans[1].group(0)}
    if grace:
        out["late_grace"] = grace.group(1)
    return out, None


def _parse_leave(text: str):
    out = {}
    for key, word in LEAVE_WORDS:
        match = re.search(rf"(?:{word})\D{{0,14}}{NUM}", text, re.IGNORECASE)
        if match:
            out[key] = match.group(1)
    return (out, None) if out else (None, "Give the days per year for each leave type, for example: casual 10, sick 14, earned 18, maternity 112. Use your own policy.")


def _parse_structure(text: str):
    def grab(pattern):
        match = re.search(pattern + r"\D{0,14}" + NUM, text, re.IGNORECASE)
        return match.group(1) if match else None

    basic = grab(r"basic")
    if not basic:
        return None, "Tell me Basic as a percent of the gross salary, for example: basic 60, house rent 20, medical 1500, conveyance 1000."
    out = {"structure_name": "Standard Structure", "basic_pct": basic}
    for key, pattern in (("hra_pct", r"(?:hra|house\s*rent)"), ("medical_amount", r"medical"), ("conveyance_amount", r"(?:conveyance|transport)")):
        value = grab(pattern)
        if value:
            out[key] = value
    named = re.search(r"\bname[d]?\s*[:=]?\s*([A-Za-z][\w ]{2,40}?)(?:,|$|\s+basic)", text, re.IGNORECASE)
    if named:
        out["structure_name"] = named.group(1).strip()
    return out, None


def _choices(key: str, env: dict, answers: dict):
    """Radio buttons for a single answer, checkboxes for several: what the chat draws under the question."""
    if key == "language":
        return {"type": "single", "options": [{"label": "English", "value": "English"}, {"label": sp.LANGUAGES["bn"], "value": "Bangla"}]}
    if key == "industry":
        return {"type": "single", "options": [{"label": i["label"], "value": i["label"]} for i in env["industries"]]}
    if key == "weekly_off":
        usual = set(answers.get("weekly_off") or sp.suggest_weekly_off(answers.get("country")))
        return {"type": "multi", "options": [{"label": d, "value": d, "checked": d in usual} for d in sp.WEEKDAYS]}
    if key == "holidays":
        country, count = answers.get("country"), None
        if country and env.get("country_holiday_count"):
            count = env["country_holiday_count"](country)
        if count:
            return {"type": "single", "options": [{"label": f"Add the {count} public holidays of {country}", "value": "Yes, add them"},
                                                  {"label": "I will list my own", "value": "I will list my own"}]}
    return None


def _question(i: int, env, answers: dict) -> tuple[str, list[str]]:
    key = STEPS[i]
    head = f"**{i + 1} of {len(STEPS)}. "
    if key == "country":
        now = env["current_country"]
        return head + "Which country is your company in?**" + (f"\nYour company is saved as {now}. Reply with the same, or a different country." if now else ""), ([now] if now else [])
    if key == "language":
        return head + "Which language do you want to work in?** Choose one.", ["skip"]
    if key == "locations":
        return head + "Where do you work? Give your offices, factories or sites.**\nFor example: Head Office, Dhaka Factory. They become your branches.", ["skip"]
    if key == "industry":
        return head + "What does your company do?** Choose one below, or just tell me what you do.", ["skip"]
    if key == "extra_departments":
        return head + "Which departments do you have?**\nSeparate them with commas. Your industry's usual departments are added too.", ["skip"]
    if key == "extra_titles":
        return head + "Which job titles do you have?**\nSeparate them with commas.", ["skip"]
    if key == "weekly_off":
        usual = sp.suggest_weekly_off(answers.get("country"))
        return head + "Which days are your weekly off?** Tick every day that applies.\nThe usual for your country is " + " and ".join(usual) + ".", ["skip"]
    if key == "holidays":
        country, count = answers.get("country"), None
        if country and env.get("country_holiday_count"):
            count = env["country_holiday_count"](country)
        if count:
            return (head + f"Public holidays for {env['year']}.**\nReckonERP's holiday calendar has {count} public holidays for {country}. "
                    "Choose below, or type your own list (date first, one per line). I will not guess any dates."), ["skip"]
        return head + f"List your public holidays for {env['year']}, one per line, date first.**\nFor example: {env['year']}-03-26 Independence Day. I will not guess any dates.", ["skip"]
    if key == "shift":
        return head + "What are your working hours?** Give a shift name, start and end time.\nFor example: General Shift 09:00 to 17:30, grace 10 minutes.", ["skip"]
    if key == "leave":
        return head + "How many leave days per year for each type, by your policy?**\nFor example: casual 10, sick 14, earned 18, maternity 112. Leave out any type you do not want.", ["skip"]
    return head + "How should the salary structure be built?**\nBasic and house rent as a percent of the gross, medical and conveyance as fixed monthly amounts.\nFor example: basic 60, house rent 20, medical 1500, conveyance 1000.", ["skip"]


def _echo(key: str, value: dict, env: dict) -> str:
    """What was understood, in words, so the person can catch a misreading at once."""
    if key == "language":
        return sp.LANGUAGES[value["language"]]
    if key == "industry":
        return next((i["label"] for i in env["industries"] if i["key"] == value["industry"]), value["industry"])
    if key == "weekly_off":
        return " and ".join(value["weekly_off"])
    if key == "shift":
        return f"{value['shift_name']}, {value['shift_start']} to {value['shift_end']}" + (f", grace {value['late_grace']} min" if value.get("late_grace") else "")
    if key == "leave":
        names = {k: label for k, label in sp.LEAVE_QUESTIONS}
        return ", ".join(f"{names[k].replace(' Leave', '')} {v}" for k, v in value.items())
    if key == "structure":
        parts = [f"basic {value['basic_pct']}%"]
        if value.get("hra_pct"):
            parts.append(f"house rent {value['hra_pct']}%")
        for field, label in (("medical_amount", "medical"), ("conveyance_amount", "conveyance")):
            if value.get(field):
                parts.append(f"{label} {value[field]}")
        return ", ".join(parts)
    return ", ".join(f"{v}" if not isinstance(v, list) else " and ".join(v) for v in value.values())


def _summary(plan: dict) -> str:
    rows = []
    for step in plan["steps"]:
        mark = {"ready": "✓", "attention": "!", "skipped": "–"}.get(step["status"], "–")
        items = "; ".join(step["items"][:4]) if step["status"] != "skipped" else "skipped"
        rows.append(f"{mark} **{step['title']}**: {items}" + (f"\n   _{step['note']}_" if step["status"] == "attention" and step["note"] else ""))
    return "\n".join(rows)


def _confirmed(text: str) -> bool:
    low = text.strip().casefold().strip(".!")
    return low in YES or low.startswith("yes")


def turn(message: str, state, env: dict) -> dict:
    """One chat turn. ``env`` keys: countries, industries, year, current_country, build_plan(answers), apply(answers), ai_holidays(text)."""
    st = _clean_state(state)
    text = sp.clean_text(message, 4000)
    low = text.casefold().strip()
    answers = st["answers"]

    def out(reply, replies=(), done=False, choices="auto"):
        st["phase"] = "done" if done else st["phase"]
        if choices == "auto":
            if done:
                choices = None
            elif st["phase"] == "review":
                choices = {"type": "single", "options": [{"label": "Yes, set everything up", "value": "Yes, set everything up"},
                                                         {"label": "Change an answer", "value": "Change an answer"}]}
                replies = ()
            elif st["idx"] < len(STEPS):
                choices = _choices(STEPS[st["idx"]], env, answers)
                if choices:
                    replies = [r for r in replies if r.casefold() == "skip"]
            else:
                choices = None
        return {"reply": reply, "state": None if done else st, "replies": list(replies)[:8], "done": done, "choices": choices}

    def page_link(message):
        """The menu name for a page the person asked for; Aura turns it into a link."""
        if not re.search(r"\b(link|page|open|where|show)\b", message, re.IGNORECASE):
            return None
        for word, label in PAGE_LINKS:
            if word in message.casefold():
                return label
        return None

    def ask_next():
        if st["idx"] >= len(STEPS):
            plan = env["build_plan"](answers)
            bad = [s for s in plan["steps"] if s["status"] == "attention"]
            if bad:
                # Fix what cannot run first, right here, instead of asking the person to name a step.
                question_key = PLAN_STEP_TO_QUESTION.get(bad[0]["key"], bad[0]["key"])
                if question_key in STEPS:
                    st["idx"], st["phase"], st["fixing"] = STEPS.index(question_key), "ask", True
                    for k in STEP_KEYS.get(question_key, ()):
                        answers.pop(k, None)
                    question, replies = _question(st["idx"], env, answers)
                    return out(f"One thing needs fixing before I can set this up: {bad[0]['note'] or bad[0]['title']}\n\n" + question, replies)
            st["phase"], st["fixing"] = "review", False
            reply = "Here is your setup plan. Nothing has been created yet.\n\n" + _summary(plan)
            return out(reply + "\n\nReply **yes** to set everything up, or say which step to change.", ["Yes, set everything up", "Change an answer"])
        question, replies = _question(st["idx"], env, answers)
        return out(question, replies)

    begin = re.fullmatch(r"(?:start|restart|begin)(?: at| with)?(?: ([a-z_ ]+))?", low)
    if not st["started"] or begin:
        wanted = (begin.group(1) or "").strip().replace(" ", "_") if begin else ""
        first = STEPS.index(wanted) if wanted in STEPS else 0
        st = {"idx": first, "answers": {}, "phase": "ask", "started": True, "fixing": False}
        answers = st["answers"]
        question, replies = _question(first, env, answers)
        return out(f"I will set up HR and payroll for **{env['company']}** by asking a few questions, then do the setup for you. "
                   "Answer in your own words, say `skip` to skip a question or `back` to go back. Nothing is created until you confirm at the end.\n\n" + question, replies)
    if low in ("cancel", "stop", "quit", "exit"):
        return out("Stopped. Nothing was changed. Start again any time from the Ask AI button.", done=True)

    if st["phase"] == "review":
        if _confirmed(text):
            result = env["apply"](answers)
            lines = [f"{'✓' if r['result'] == 'done' else '!' if r['result'] == 'failed' else '–'} **{r['label']}**: {r['message'] or r['result']}" for r in result["results"]]
            head = f"Done: {result['done']} steps set up" + (f", {result['failed']} failed" if result["failed"] else "") + "."
            return out(head + "\n\n" + "\n".join(lines) + "\n\nReview or edit any step here: Holiday List, Branch, Department, Designation, Shift Type, Salary Structure. "
                       "The Guided setup tab in HR Studio and Payroll Studio now shows each step with its own link. Next you can add your employees and give them the salary structure.", done=True)
        # Only a clear change request, or a step name on its own, reopens a step. A question or a request for a page does not.
        for i, key in enumerate(STEPS):
            named = TITLES[key].casefold() == low or key.replace("_", " ") == low or (CHANGE_WORDS.search(text) and (TITLES[key].casefold() in low or key.replace("_", " ") in low))
            if named:
                st["idx"], st["phase"], st["fixing"] = i, "ask", True
                for k in STEP_KEYS.get(key, ()):
                    answers.pop(k, None)
                question, replies = _question(i, env, answers)
                return out("Okay, let us redo that one.\n\n" + question, replies)
        link = page_link(text)
        if link:
            return out(f"You can open {link} any time. I am still waiting on the plan above: reply **yes** to set everything up, or say which step to change.",
                       ["Yes, set everything up", "Change an answer"])
        if low in ("change an answer", "change", "edit"):
            return out("Which step do you want to change? Pick one:", choices={"type": "single", "options": [{"label": TITLES[k], "value": TITLES[k]} for k in STEPS]})
        return out("I am waiting for your go-ahead on the plan above. Reply **yes** to set everything up, or say which step to change, or `cancel` to stop.",
                   ["Yes, set everything up", "Change an answer"])

    # ---- asking
    if low == "back":
        st["idx"] = max(0, st["idx"] - 1)
        question, replies = _question(st["idx"], env, answers)
        return out(question, replies)
    key = STEPS[st["idx"]]
    link = page_link(text)
    if link:
        question, replies = _question(st["idx"], env, answers)
        return out(f"You can open {link} any time. Back to the setup:\n\n{question}", replies)
    if low in SKIP:
        for k in STEP_KEYS.get(key, ()):
            answers.pop(k, None)
        if key == "weekly_off":
            answers["weekly_off"] = sp.suggest_weekly_off(answers.get("country"))  # the plan shows the days it will use
        st["idx"] = len(STEPS) if st.get("fixing") else st["idx"] + 1
        return ask_next()

    value, error = None, None
    if key == "country":
        picked, error = _pick_country(text, env["countries"])
        value = {"country": picked} if picked else None
    elif key == "language":
        if re.search(r"bangla|bengali|\bbn\b|বাংলা", low):
            value = {"language": "bn"}
        elif re.search(r"english|\ben\b", low):
            value = {"language": "en"}
        else:
            error = "Please choose English or Bangla."
    elif key == "locations":
        names = sp.split_names(text)
        value, error = ({"locations": ", ".join(names)}, None) if names else (None, "Give one or more names, separated by commas, or say skip.")
    elif key == "industry":
        picked, error = _pick_industry(text, env["industries"])
        value = {"industry": picked} if picked else None
        if error:
            error = "I could not tell which industry fits. Choose one below, or describe what your company does."
    elif key in ("extra_departments", "extra_titles"):
        names = sp.split_names(text)
        value, error = ({key: ", ".join(names)}, None) if names else (None, "Give one or more names, separated by commas, or say skip.")
    elif key == "weekly_off":
        days, error = _parse_days(text, answers.get("country"))
        value = {"weekly_off": days} if days else None
    elif key == "holidays" and low in ("yes", "yes, add them", "add them", "yes please", "y", "ok") and answers.get("country"):
        value = {"holidays_country": "1"}
    elif key == "holidays" and "list my own" in low:
        return out(f"Type your holidays, one per line, date first. For example: {env['year']}-03-26 Independence Day. I will not guess any dates.", ["skip"], choices=None)
    elif key == "holidays":
        rows, unread = sp.parse_holidays(text, env["year"])
        if unread and env.get("ai_holidays"):
            lines = env["ai_holidays"]("\n".join(unread))
            more, unread = sp.parse_holidays("\n".join(lines), env["year"]) if lines else ([], unread)
            rows = rows + more
        if rows and not unread:
            value = {"holidays": "\n".join(f"{h['date']} {h['name']}" for h in rows)}
        else:
            error = ("I could not read these lines: " + "; ".join(unread[:4]) + f". Please write each as date then name, for example {env['year']}-03-26 Independence Day.") if unread else \
                f"Please write each holiday as date then name, for example {env['year']}-03-26 Independence Day."
    elif key == "shift":
        value, error = _parse_shift(text)
    elif key == "leave":
        value, error = _parse_leave(text)
    elif key == "structure":
        value, error = _parse_structure(text)
    if error or not value:
        question, replies = _question(st["idx"], env, answers)
        return out(f"{error or 'I could not read that.'}\n\n{question}", replies)
    answers.update(value)
    st["idx"] = len(STEPS) if st.get("fixing") else st["idx"] + 1
    shown = _echo(key, value, env)
    nxt = ask_next()
    nxt["reply"] = f"✓ {TITLES[key]}: {shown[:160]}\n\n" + nxt["reply"]
    return nxt
