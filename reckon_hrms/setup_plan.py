"""The setup interview: questions for every step, and the plan they turn into (pure: no Frappe, so it is unit-tested).

People answer plain questions; ``build_plan`` turns the answers into a list of steps that a person reviews before
anything is created. Nothing here invents a number: a question left empty means that step is skipped. Free text that
cannot be read is listed for attention instead of being guessed.
"""

from __future__ import annotations

import re
from datetime import date, datetime

WEEKDAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
MAX_LIST = 40
MAX_HOLIDAYS = 60
LEAVE_QUESTIONS = (("leave_casual", "Casual Leave"), ("leave_sick", "Sick Leave"), ("leave_earned", "Earned Leave"),
                   ("leave_maternity", "Maternity Leave"))

LANGUAGES = {"en": "English", "bn": "বাংলা (Bangla)"}
# The usual weekly off in a country, offered as a starting tick the person confirms. Never applied silently.
WEEKLY_OFF_BY_COUNTRY = {
    "Bangladesh": ["Friday"], "India": ["Sunday"], "Pakistan": ["Sunday"],
    "Saudi Arabia": ["Friday", "Saturday"], "Qatar": ["Friday", "Saturday"], "Kuwait": ["Friday", "Saturday"],
}
DEFAULT_WEEKLY_OFF = ["Saturday", "Sunday"]


def suggest_weekly_off(country) -> list[str]:
    return list(WEEKLY_OFF_BY_COUNTRY.get(clean_text(country, 60), DEFAULT_WEEKLY_OFF))


# key, studio, kind, label, help. The page asks these in order, one at a time; the plan below reads the same keys.
QUESTIONS = [
    {"key": "country", "studio": "both", "kind": "country", "label": "Which country is your company in?",
     "help": "Used for the usual weekly off and as context for Ask AI. It is saved on the company only if the company has none yet."},
    {"key": "language", "studio": "both", "kind": "language", "label": "Which language do you want to work in?",
     "help": "Ask AI answers in this language and your screens use it. This is your own setting."},
    {"key": "locations", "studio": "both", "kind": "list", "label": "Where do you work? Offices, factories or sites",
     "help": "One name each, for example Head Office, Dhaka Factory. They become your Branch list. Leave empty to skip."},
    {"key": "extra_departments", "studio": "both", "kind": "list", "label": "Which departments do you have?",
     "help": "Separate with commas or new lines. Your industry's starter departments are added too; leave empty to keep only those."},
    {"key": "extra_titles", "studio": "both", "kind": "list", "label": "Which job titles do you have?",
     "help": "Separate with commas or new lines. Leave empty to keep only the starter ones."},
    {"key": "weekly_off", "studio": "both", "kind": "days", "label": "Weekly off days",
     "help": "Which days are the weekly off? The usual days for your country are ticked first; change them if yours differ."},
    {"key": "holidays", "studio": "both", "kind": "text", "label": "Public holidays this year",
     "help": "One per line, date first, for example: 2026-03-26 Independence Day. Leave empty to add none."},
    {"key": "shift_name", "studio": "both", "kind": "shift", "label": "Working hours",
     "help": "Give the shift a name and its start and end time. Leave the name empty to skip."},
    {"key": "leave_casual", "studio": "both", "kind": "leave", "label": "Leave days per year",
     "help": "Days per year for each type, from your own policy. Leave a type empty to skip it. Nothing is given to employees yet."},
    {"key": "rule_marks", "studio": "payroll", "kind": "rules", "label": "How should late entry and early exit be deducted?",
     "help": "Every this many marks equal one day, a day's pay is base salary divided by a number, and an optional monthly cap. "
             "Nothing is deducted by saving this rule."},
    {"key": "structure_name", "studio": "payroll", "kind": "structure", "label": "Salary structure",
     "help": "Basic and house rent as a percent of the gross salary, medical and conveyance as fixed monthly amounts. "
             "Leave the name empty to skip. Amounts per person are set when you give the structure to people."},
]


def clean_text(value, limit: int = 4000) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value or "")).strip()[:limit]


def same(a: str, b: str) -> bool:
    """Two names are the same when they differ only in case or spacing."""
    return re.sub(r"\s+", " ", str(a)).strip().casefold() == re.sub(r"\s+", " ", str(b)).strip().casefold()


def missing(names: list[str], have) -> list[str]:
    """The names that the company does not have yet (case and spacing ignored)."""
    keys = {re.sub(r"\s+", " ", str(h)).strip().casefold() for h in have}
    return [n for n in names if re.sub(r"\s+", " ", n).strip().casefold() not in keys]


_DEPT_NOISE = {"and", "department", "departments", "dept", "team", "division", "the", "of"}
_DEPT_SYNONYMS = {"hr": ("human", "resources")}


def _dept_tokens(name: str) -> frozenset:
    words = re.sub(r"[^a-z0-9 ]+", " ", str(name).casefold().replace("&", " and ")).split()
    out = []
    for w in words:
        out.extend(_DEPT_SYNONYMS.get(w, (w,)))
    return frozenset(w for w in out if w not in _DEPT_NOISE)


def similar_department(name: str, have) -> str | None:
    """The existing department that means the same as ``name`` ("Sales" and "Sales & Marketing", "Finance" and
    "Accounts and Finance"), else None. Words are compared, not spelling: the shorter name's words must all be in the longer."""
    mine = _dept_tokens(name)
    if not mine:
        return None
    for other in have:
        theirs = _dept_tokens(other)
        small, big = sorted((mine, theirs), key=len)
        if small and small <= big and len(big) <= 3:
            return str(other)
    return None


def split_names(text, limit: int = MAX_LIST) -> list[str]:
    """Names separated by commas, semicolons or new lines: trimmed, no repeats, in the order given."""
    seen, out = set(), []
    for part in re.split(r"[,;\n]+", clean_text(text)):
        name = re.sub(r"\s+", " ", part).strip(" .-")
        if name and len(name) <= 80 and name.casefold() not in seen:
            seen.add(name.casefold())
            out.append(name)
    return out[:limit]


def _number(value, low: float, high: float):
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "").strip())
    except ValueError:
        return None
    return number if low <= number <= high else None


def _time(value):
    text = clean_text(value, 8)
    match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?", text)
    return f"{int(match[1]):02d}:{match[2]}:00" if match else None


_DATE_FORMS = (("%Y-%m-%d", re.compile(r"^(\d{4}-\d{1,2}-\d{1,2})")), ("%d-%m-%Y", re.compile(r"^(\d{1,2}-\d{1,2}-\d{4})")),
               ("%d/%m/%Y", re.compile(r"^(\d{1,2}/\d{1,2}/\d{4})")))


def parse_holidays(text, year: int) -> tuple[list[dict], list[str]]:
    """Holiday lines: ``date name``. Returns the holidays that read cleanly and the lines that did not."""
    holidays, unread, seen = [], [], set()
    for line in clean_text(text).splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = None
        for fmt, pattern in _DATE_FORMS:
            match = pattern.match(line)
            if match:
                try:
                    parsed = (datetime.strptime(match[1], fmt).date(), line[match.end():].strip(" -:,\t"))
                except ValueError:
                    parsed = None
                break
        if not parsed or parsed[0].year != year or not parsed[1]:
            unread.append(line[:120])
            continue
        if parsed[0] in seen:
            continue
        seen.add(parsed[0])
        holidays.append({"date": parsed[0].isoformat(), "name": parsed[1][:80]})
    return sorted(holidays, key=lambda h: h["date"])[:MAX_HOLIDAYS], unread[:10]


def normalize_answers(raw, year: int | None = None) -> dict:
    """Clean what the person typed. Anything unreadable becomes empty, never a guess."""
    raw = raw if isinstance(raw, dict) else {}
    year = year or date.today().year
    days = raw.get("weekly_off")
    days = [d for d in (days if isinstance(days, list) else [days]) if d in WEEKDAYS] if days else []
    holidays, unread = parse_holidays(raw.get("holidays"), year)
    out = {
        "industry": clean_text(raw.get("industry"), 60),
        "country": clean_text(raw.get("country"), 60),
        "language": raw.get("language") if raw.get("language") in LANGUAGES else "",
        "locations": split_names(raw.get("locations")),
        "extra_departments": split_names(raw.get("extra_departments")),
        "extra_titles": split_names(raw.get("extra_titles")),
        "weekly_off": days if "weekly_off" in raw else [],
        "weekly_asked": "weekly_off" in raw,
        "holidays": holidays, "holidays_unread": unread, "year": year,
        "holidays_country": str(raw.get("holidays_country") or "").strip().casefold() in ("1", "true", "yes", "on"),
        "shift": None,
        "leave": {},
        "structure": None,
        "rules": None,
    }
    marks, divisor = _number(raw.get("rule_marks"), 1, 31), _number(raw.get("rule_divisor"), 1, 31)
    if marks or divisor:
        out["rules"] = {"marks_per_day": int(marks or 0), "divisor": int(divisor or 0), "cap": _number(raw.get("rule_cap"), 0, 10_000_000) or 0}
    name = clean_text(raw.get("shift_name"), 60)
    start, end = _time(raw.get("shift_start")), _time(raw.get("shift_end"))
    if name and start and end:
        out["shift"] = {"name": name, "start": start, "end": end, "grace": int(_number(raw.get("late_grace"), 0, 180) or 0)}
    elif name:
        out["shift_problem"] = "Add a start and an end time for the shift, for example 09:00 and 17:00."
    for key, leave_type in LEAVE_QUESTIONS:
        days_per_year = _number(raw.get(key), 0.5, 365)
        if days_per_year:
            out["leave"][leave_type] = days_per_year
    sname = clean_text(raw.get("structure_name"), 60)
    if sname:
        basic, hra = _number(raw.get("basic_pct"), 1, 100), _number(raw.get("hra_pct"), 0, 100)
        out["structure"] = {"name": sname, "basic_pct": basic, "hra_pct": hra or 0,
                            "medical": _number(raw.get("medical_amount"), 0, 10_000_000) or 0,
                            "conveyance": _number(raw.get("conveyance_amount"), 0, 10_000_000) or 0}
    return out


def structure_problem(structure: dict | None) -> str | None:
    if not structure:
        return None
    if not structure["basic_pct"]:
        return "Add what percent of the gross salary is Basic."
    if structure["basic_pct"] + structure["hra_pct"] > 100:
        return "Basic and house rent together are more than 100% of the gross salary."
    return None


def _rules_line(rules: dict) -> str:
    cap = f"capped at {rules['cap']:g} a month" if rules["cap"] else "no monthly cap"
    return f"Every {rules['marks_per_day']} late or early marks = 1 day; a day's pay is base salary / {rules['divisor']}; {cap}"


def _there(wanted: list[str], new: list[str]) -> list[str]:
    """The wanted names that already exist, shown as "X (already there)"."""
    return [f"{n} (already there)" for n in wanted if n not in new]


def build_plan(answers: dict, segment: dict | None, company: str, existing: dict | None = None) -> dict:
    """Turn clean answers into reviewable steps. ``existing`` marks names the company already has (sets)."""
    existing = existing or {}
    steps = []

    def step(key, title, items, status="ready", note=""):
        steps.append({"key": key, "title": title, "items": items, "status": status, "note": note})

    if segment:
        step("industry", f"Industry: {segment['label']}",
             [(f"{len(segment['roles'])} job titles, {len(segment['departments'])} departments, {len(segment['components'])} pay items and "
               f"{len(segment['leave_types'])} leave types are added where missing")])
    else:
        step("industry", "Industry", [], "skipped", "No industry chosen, so no starter items are added.")
    country = answers["country"]
    step("country", f"Country: {country}" if country else "Country",
         [f"Saved on the company if it has none yet. Usual weekly off: {', '.join(suggest_weekly_off(country))}"] if country else ["Nothing to add"],
         "ready" if country else "skipped")
    step("language", "Language", [LANGUAGES[answers["language"]]] if answers["language"] else ["Nothing to add"],
         "ready" if answers["language"] else "skipped", "This changes your own language setting only." if answers["language"] else "")
    have = existing.get("branches", set())
    new_locations = missing(answers["locations"], have)
    step("locations", "Locations (branches)", [*new_locations, *_there(answers["locations"], new_locations)] or ["Nothing to add"],
         "ready" if new_locations else "skipped", "" if new_locations or not answers["locations"] else "Already set up. Edit them in Branch.")
    have = existing.get("departments", set())
    new_departments, lines, seen = [], [], []
    for d in answers["extra_departments"]:
        twin = similar_department(d, [*have, *seen])
        if twin:
            lines.append(f"{d} (already there)" if same(d, twin) else f"{d} (same as {twin}, not added)")
        else:
            new_departments.append(d)
            seen.append(d)
    step("departments", "Departments", [*new_departments, *lines] or ["Nothing to add"],
         "ready" if new_departments else "skipped", "" if new_departments or not answers["extra_departments"] else "Already set up. Edit them in Department.")
    have = existing.get("designations", set())
    new_titles = missing(answers["extra_titles"], have)
    step("titles", "Job titles", [*new_titles, *_there(answers["extra_titles"], new_titles)] or ["Nothing to add"],
         "ready" if new_titles else "skipped", "" if new_titles or not answers["extra_titles"] else "Already set up. Edit them in Designation.")

    if not answers["weekly_asked"] and not answers["holidays"] and not answers["holidays_country"] and not answers["holidays_unread"]:
        step("holidays", f"Holiday calendar {answers['year']}", ["Nothing to add"], "skipped")
        holiday_items = None
    else:
        holiday_items = [f"Weekly off: {', '.join(answers['weekly_off']) or 'none'}"]
    count = existing.get("country_holidays")
    if holiday_items is not None:
        note = ""
        if answers["holidays_country"] and answers["country"]:
            if count:
                holiday_items.append(f"The {count} public holidays of {answers['country']} from the ReckonERP holiday calendar")
            else:
                holiday_items.append(f"Public holidays of {answers['country']} from the ReckonERP holiday calendar")
                note = f"ReckonERP has no holiday calendar for {answers['country']}. Add the holidays by hand instead." if count == 0 else ""
        holiday_items += [f"{h['date']}  {h['name']}" for h in answers["holidays"]]
        if answers["holidays_unread"]:
            note = "These lines could not be read (use date first, in this year): " + "; ".join(answers["holidays_unread"])
        step("holidays", f"Holiday calendar {answers['year']}", holiday_items,
             "attention" if answers["holidays_unread"] else "ready", note)
    if answers["shift"]:
        s = answers["shift"]
        line = f"{s['name']}: {s['start'][:5]} to {s['end'][:5]}" + (f", late entry after {s['grace']} min" if s["grace"] else "")
        twin = next((x for x in existing.get("shifts", []) if same(x["name"], s["name"]) or (x["start"][:5] == s["start"][:5] and x["end"][:5] == s["end"][:5])), None)
        if twin:
            step("shift", "Working hours", [line], "skipped",
                 f"Already set up: {twin['name']} ({twin['start'][:5]} to {twin['end'][:5]}). A second shift is not added. Edit it in Shift Type.")
        else:
            step("shift", "Working hours", [line])
    elif answers.get("shift_problem"):
        step("shift", "Working hours", [], "attention", answers["shift_problem"])
    else:
        step("shift", "Working hours", ["Nothing to add"], "skipped")
    if answers["leave"] and existing.get("leave_policy"):
        step("leave", "Leave policy", [f"{k}: {v:g} days a year" for k, v in answers["leave"].items()], "skipped",
             f"Already set up ({existing['leave_policy']}). It is not changed here: edit the days in Leave Policy.")
    elif answers["leave"]:
        step("leave", "Leave policy", [f"{k}: {v:g} days a year" for k, v in answers["leave"].items()],
             "ready", "Employees get these days when you assign the policy to them. Nothing is given now.")
    else:
        step("leave", "Leave policy", ["Nothing to add"], "skipped")
    problem = structure_problem(answers["structure"])
    if answers["structure"] and not problem:
        s = answers["structure"]
        other = round(100 - s["basic_pct"] - s["hra_pct"], 2)
        items = [f"Basic Salary: {s['basic_pct']:g}% of gross", f"House Rent Allowance: {s['hra_pct']:g}% of gross"]
        if s["medical"]:
            items.append(f"Medical Allowance: {s['medical']:g} fixed")
        if s["conveyance"]:
            items.append(f"Conveyance Allowance: {s['conveyance']:g} fixed")
        have_structures = existing.get("structures", [])
        if any(same(x, s["name"]) for x in have_structures):
            step("structure", f"Salary structure: {s['name']}", items, "skipped",
                 "Already set up with this name. It is not changed here: edit it in Salary Structure.")
        else:
            others = f" You already have: {', '.join(have_structures[:3])}; this adds another." if have_structures else ""
            step("structure", f"Salary structure: {s['name']}", items, "ready",
                 "Amounts per person come from each person's gross when you give them the structure." +
                 (f" {other:g}% of the gross has no pay item yet." if other > 0 else "") + others)
    elif problem:
        step("structure", "Salary structure", [], "attention", problem)
    else:
        step("structure", "Salary structure", ["Nothing to add"], "skipped")
    rules = answers["rules"]
    if rules:
        if not (rules["marks_per_day"] and rules["divisor"]):
            step("rules", "Attendance deduction rule", [], "attention", "Give both: how many late or early marks equal one day, and the divisor for a day's pay (for example 30).")
        elif existing.get("rules") and existing["rules"] == {"marks_per_day": rules["marks_per_day"], "divisor": rules["divisor"], "cap": float(rules["cap"])}:
            step("rules", "Attendance deduction rule", [_rules_line(rules)], "skipped", "Already set up with these values. Edit them in Payroll Studio > Guided setup.")
        else:
            step("rules", "Attendance deduction rule", [_rules_line(rules)], "ready", "Used when HR approves late and early deductions for a run. Nothing is deducted by saving this.")
    else:
        step("rules", "Attendance deduction rule", ["Nothing to add"], "skipped")
    return {"company": company, "steps": steps,
            "ready": sum(1 for s in steps if s["status"] == "ready"),
            "attention": sum(1 for s in steps if s["status"] == "attention")}


def parse_ai_holidays(data, year: int) -> list[str]:
    """Holiday lines from the AI's reading of free text: only well-formed dates in the year survive."""
    lines = []
    for row in data if isinstance(data, list) else []:
        if not isinstance(row, dict):
            continue
        try:
            when = datetime.strptime(str(row.get("date")), "%Y-%m-%d").date()
        except ValueError:
            continue
        name = clean_text(row.get("name"), 80)
        if when.year == year and name:
            lines.append(f"{when.isoformat()} {name}")
    return lines[:MAX_HOLIDAYS]
