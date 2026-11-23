"""The setup agent in the Ask AI chat: it asks, reads replies, confirms, then applies (no Frappe)."""

import unittest

from reckon_hrms import setup_chat as sc
from reckon_hrms import setup_plan as sp

SEGMENTS = [{"key": "it_software", "label": "IT / Software"}, {"key": "healthcare", "label": "Healthcare"}]


def make_env(applied=None):
    def build_plan(answers):
        clean = sp.normalize_answers(answers, 2026)
        return sp.build_plan(clean, {"label": "IT / Software", "roles": [], "departments": [], "components": [], "leave_types": []} if clean["industry"] else None, "Acme")

    def apply(answers):
        if applied is not None:
            applied.append(answers)
        return {"done": 2, "failed": 0, "results": [{"key": "country", "label": "Country", "result": "done", "message": "ok"}]}

    return {"company": "Acme", "countries": ["Bangladesh", "India", "United Kingdom", "United States"], "industries": SEGMENTS, "year": 2026,
            "current_country": "", "build_plan": build_plan, "apply": apply, "ai_holidays": None}


def say(text, state, env):
    return sc.turn(text, state, env)


class ChatTests(unittest.TestCase):
    def test_it_starts_by_asking_the_country_and_says_nothing_is_created_yet(self):
        r = say("start", None, make_env())
        self.assertIn("Which country", r["reply"])
        self.assertIn("Nothing is created until you confirm", r["reply"])
        self.assertEqual(r["state"]["idx"], 0)

    def test_questions_come_in_the_asked_order(self):
        self.assertEqual(sc.STEPS[:4], ["country", "language", "locations", "industry"])
        self.assertEqual(sc.STEPS[4], "extra_departments")

    def test_each_reply_is_read_and_the_next_question_follows(self):
        env, r = make_env(), say("start", None, make_env())
        r = say("bangladesh", r["state"], env)
        self.assertIn("✓ Country: Bangladesh", r["reply"])
        self.assertIn("Which language", r["reply"])
        r = say("Bangla please", r["state"], env)
        self.assertEqual(r["state"]["answers"]["language"], "bn")
        r = say("Head Office, Dhaka Factory", r["state"], env)
        self.assertEqual(r["state"]["answers"]["locations"], "Head Office, Dhaka Factory")
        r = say("2", r["state"], env)
        self.assertEqual(r["state"]["answers"]["industry"], "healthcare")

    def test_a_reply_that_cannot_be_read_is_asked_again_not_guessed(self):
        env, r = make_env(), say("start", None, make_env())
        r = say("Atlantis", r["state"], env)
        self.assertIn("could not find that country", r["reply"])
        self.assertEqual(r["state"]["idx"], 0)
        self.assertNotIn("country", r["state"]["answers"])

    def test_skip_and_back(self):
        env, r = make_env(), say("start", None, make_env())
        r = say("skip", r["state"], env)
        self.assertEqual(r["state"]["idx"], 1)
        r = say("back", r["state"], env)
        self.assertEqual(r["state"]["idx"], 0)

    def run_all(self, env):
        r = say("start", None, env)
        for reply in ("India", "english", "Main Office", "1", "Legal", "Intern", "friday and saturday", "2026-03-26 Independence Day",
                      "General Shift 09:00 to 17:30, grace 10 minutes", "casual 10, sick 14, earned 18, maternity 112"):
            r = say(reply, r["state"], env)
        return r

    def test_the_last_answer_shows_the_plan_and_waits_for_a_yes(self):
        applied = []
        r = self.run_all(make_env(applied))
        self.assertIn("Here is your setup plan", r["reply"])
        self.assertIn("Nothing has been created yet", r["reply"])
        self.assertEqual([o["value"] for o in r["choices"]["options"]], ["Yes, set everything up", "Change an answer"])
        self.assertEqual(r["choices"]["type"], "single")
        self.assertEqual(applied, [])
        a = r["state"]["answers"]
        self.assertEqual((a["shift_start"], a["shift_end"], a["late_grace"]), ("09:00", "17:30", "10"))
        self.assertEqual((a["leave_casual"], a["leave_maternity"]), ("10", "112"))
        self.assertNotIn("structure_name", a)  # the salary structure is a payroll question, not an HR one
        self.assertEqual(a["weekly_off"], ["Friday", "Saturday"])

    def test_yes_applies_once_and_ends_the_chat(self):
        applied, env = [], make_env([])
        env = make_env(applied)
        r = self.run_all(env)
        done = say("Yes, set everything up", r["state"], env)
        self.assertTrue(done["done"])
        self.assertIsNone(done["state"])
        self.assertEqual(len(applied), 1)
        self.assertEqual(applied[0]["country"], "India")
        self.assertIn("Done: 2 steps set up", done["reply"])

    def test_anything_but_a_yes_does_not_apply(self):
        applied = []
        env = make_env(applied)
        r = self.run_all(env)
        r = say("hmm maybe later", r["state"], env)
        self.assertEqual(applied, [])
        self.assertIn("waiting for your go-ahead", r["reply"])
        r = say("change an answer", r["state"], env)
        self.assertIn("Which step", r["reply"])
        r = say("change holidays", r["state"], env)
        self.assertIn("redo that one", r["reply"])
        self.assertEqual(r["state"]["idx"], sc.STEPS.index("holidays"))

    def test_cancel_stops_without_changing_anything(self):
        applied = []
        env = make_env(applied)
        r = say("start", None, env)
        r = say("cancel", r["state"], env)
        self.assertTrue(r["done"])
        self.assertEqual(applied, [])

    def test_a_tampered_state_is_cleaned(self):
        st = sc._clean_state({"idx": 999, "phase": "hack", "answers": {"x" * 80: "a", "ok": {"nested": 1}, "country": "India"}, "started": True})
        self.assertEqual((st["idx"], st["phase"]), (len(sc.STEPS), "ask"))
        self.assertEqual(st["answers"], {"country": "India"})

    def test_skipping_weekly_off_uses_the_countrys_usual_days_and_shows_them(self):
        env = make_env()
        r = say("start", None, env)
        r = say("Bangladesh", r["state"], env)
        r["state"]["idx"] = sc.STEPS.index("weekly_off")
        r = say("skip", r["state"], env)
        self.assertEqual(r["state"]["answers"]["weekly_off"], ["Friday"])

    def test_shift_leave_and_structure_replies_need_what_they_need(self):
        self.assertIsNone(sc._parse_shift("General Shift")[0])
        self.assertIsNone(sc._parse_leave("many days")[0])
        self.assertIsNone(sc._parse_structure("medical 1500")[0])
        self.assertEqual(sc._parse_leave("Casual 10 and sick 14")[0], {"leave_casual": "10", "leave_sick": "14"})


if __name__ == "__main__":
    unittest.main()


class LoopTests(unittest.TestCase):
    """The loop in the screenshots: a plan with a problem, then a request for a page, sent the person round the steps again."""

    def to_review(self, env, structure="basic 60, house rent 20"):
        r = say("start", None, env)
        for reply in ("India", "english", "skip", "1", "skip", "skip", "usual", "skip", "skip", "casual 10", structure):
            r = say(reply, r["state"], env)
        return r

    def test_a_page_request_in_review_gives_the_link_and_does_not_reopen_a_step(self):
        env = make_env()
        r = self.to_review(env)
        self.assertEqual(r["state"]["phase"], "review")
        r = say("give me holidays page link", r["state"], env)
        self.assertIn("Holiday List", r["reply"])
        self.assertNotIn("redo", r["reply"])
        self.assertEqual(r["state"]["phase"], "review")

    def test_a_question_that_only_mentions_a_step_does_not_reopen_it(self):
        env = make_env()
        r = self.to_review(env)
        r = say("what are the holidays like?", r["state"], env)
        self.assertEqual(r["state"]["phase"], "review")
        self.assertIn("waiting for your go-ahead", r["reply"])

    def test_skipping_a_step_clears_its_answers_so_no_half_answer_stays_in_the_plan(self):
        env = make_env()
        r = say("start payroll", None, env)
        r["state"]["answers"].update(structure_name="Std")
        r["state"]["idx"] = sc.PAYROLL_STEPS.index("structure")
        r = say("skip", r["state"], env)
        self.assertNotIn("structure_name", r["state"]["answers"])
        self.assertEqual(r["state"]["phase"], "ask")  # on to the next payroll question
        self.assertIn("late entry and early exit", r["reply"])

    def test_a_problem_in_the_plan_asks_for_that_step_at_once(self):
        env = make_env()
        r = say("start", None, env)
        r["state"]["answers"].update(shift_name="Day")  # a shift name without times cannot run
        r["state"]["idx"] = len(sc.STEPS) - 1
        r = say("skip", r["state"], env)
        self.assertIn("One thing needs fixing", r["reply"])
        self.assertIn("working hours", r["reply"].lower())
        self.assertTrue(r["state"]["fixing"])
        after = say("General 09:00 to 17:00", r["state"], env)
        self.assertEqual(after["state"]["phase"], "review")  # straight back to the plan, no questions repeated
        self.assertEqual(after["state"]["answers"]["shift_start"], "09:00")


class CalendarTests(unittest.TestCase):
    def env(self, count):
        env = make_env()
        env["country_holiday_count"] = lambda country: count
        return env

    def to_holidays(self, env):
        r = say("start", None, env)
        for reply in ("Bangladesh", "english", "skip", "skip", "skip", "skip", "usual"):
            r = say(reply, r["state"], env)
        return r

    def test_when_erpnext_has_the_countrys_calendar_the_chat_offers_it(self):
        r = self.to_holidays(self.env(18))
        self.assertIn("18 public holidays for Bangladesh", r["reply"])
        values = [o["value"] for o in r["choices"]["options"]]
        self.assertEqual((r["choices"]["type"], values), ("single", ["Yes, add them", "I will list my own"]))
        r = say("Yes, add them", r["state"], self.env(18))
        self.assertEqual(r["state"]["answers"]["holidays_country"], "1")
        self.assertNotIn("holidays", {k for k in r["state"]["answers"] if k == "holidays"})

    def test_without_a_calendar_it_asks_for_a_list_as_before(self):
        r = self.to_holidays(self.env(0))
        self.assertIn("List your public holidays", r["reply"])

    def test_the_plan_names_the_calendar_and_the_count(self):
        a = sp.normalize_answers({"country": "Bangladesh", "holidays_country": "1"}, 2026)
        plan = sp.build_plan(a, None, "Acme", {"country_holidays": 18})
        item = next(s for s in plan["steps"] if s["key"] == "holidays")["items"]
        self.assertTrue(any("18 public holidays of Bangladesh from the ReckonERP holiday calendar" in i for i in item))
        none = sp.build_plan(a, None, "Acme", {"country_holidays": 0})
        self.assertIn("no holiday calendar", next(s for s in none["steps"] if s["key"] == "holidays")["note"])


class ChoiceTests(unittest.TestCase):
    """Single answers are radio buttons, several answers are checkboxes."""

    def at(self, key, **answers):
        env = make_env()
        r = say("start", None, env)
        r["state"]["answers"].update(answers)
        r["state"]["idx"] = sc.STEPS.index(key)
        return env, sc.turn("back", {**r["state"], "idx": sc.STEPS.index(key) + 1}, env)

    def test_language_and_industry_are_radio_buttons(self):
        _env, r = self.at("language")
        self.assertEqual(r["choices"]["type"], "single")
        self.assertEqual([o["value"] for o in r["choices"]["options"]], ["English", "Bangla"])
        _env, r = self.at("industry")
        self.assertEqual(r["choices"]["type"], "single")
        self.assertEqual([o["label"] for o in r["choices"]["options"]], [i["label"] for i in SEGMENTS])
        self.assertNotIn("1. IT", r["reply"])  # the options are buttons now, not a typed list

    def test_weekly_off_is_checkboxes_with_the_countrys_usual_days_ticked(self):
        _env, r = self.at("weekly_off", country="Bangladesh")
        self.assertEqual(r["choices"]["type"], "multi")
        ticked = [o["value"] for o in r["choices"]["options"] if o["checked"]]
        self.assertEqual(ticked, ["Friday"])
        self.assertEqual(len(r["choices"]["options"]), 7)
        _env, r = self.at("weekly_off", country="Germany")
        self.assertEqual({o["value"] for o in r["choices"]["options"] if o["checked"]}, {"Saturday", "Sunday"})

    def test_a_ticked_set_of_days_is_read_as_the_reply(self):
        env, r = self.at("weekly_off", country="Bangladesh")
        r = sc.turn("Friday, Saturday", {**r["state"], "idx": sc.STEPS.index("weekly_off")}, env)
        self.assertEqual(r["state"]["answers"]["weekly_off"], ["Friday", "Saturday"])

    def test_text_questions_have_no_buttons_and_the_skip_chip_stays_beside_radios(self):
        _env, r = self.at("locations")
        self.assertIsNone(r["choices"])
        _env, r = self.at("language")
        self.assertEqual(r["replies"], ["skip"])

    def test_choosing_to_list_my_own_asks_for_the_list_without_an_error(self):
        env = make_env()
        env["country_holiday_count"] = lambda country: 18
        r = say("start", None, env)
        r["state"]["answers"]["country"] = "Bangladesh"
        r["state"]["idx"] = sc.STEPS.index("holidays")
        r = sc.turn("I will list my own", r["state"], env)
        self.assertIn("Type your holidays", r["reply"])
        self.assertNotIn("could not", r["reply"])
        self.assertEqual(r["state"]["idx"], sc.STEPS.index("holidays"))

    def test_an_industry_that_cannot_be_told_does_not_repeat_the_list_in_the_error(self):
        env = make_env()
        r = say("start industry", None, env)
        r = say("we do many things", r["state"], env)
        self.assertIn("could not tell which industry fits", r["reply"])
        self.assertEqual(r["reply"].count("IT / Software"), 0)
        self.assertEqual(r["choices"]["type"], "single")


class PayrollFlowTests(unittest.TestCase):
    """Payroll asks only payroll questions: what HR Studio owns is never asked again."""

    def env(self, applied=None):
        env = make_env(applied)
        env["current"] = {}
        return env

    def start(self, env):
        return say("start payroll", None, env)

    def test_it_asks_only_the_salary_structure_and_the_deduction_rule(self):
        r = self.start(self.env())
        self.assertIn("3 questions", r["reply"].replace("three questions", "3 questions"))
        self.assertIn("1 of 3", r["reply"])
        self.assertIn("salary structure", r["reply"].lower())
        for hr_question in ("country", "language", "departments", "holidays", "working hours", "leave days", "Where do you work"):
            self.assertNotIn(hr_question, r["reply"].split("**1 of 3")[1], hr_question)
        self.assertEqual(r["state"]["flow"], "payroll")

    def test_the_plan_lists_only_payroll_steps_and_applying_changes_nothing_else(self):
        applied, env = [], self.env([])
        env = self.env(applied)
        r = self.start(env)
        r = say("Standard, basic 60, house rent 20, medical 1500, conveyance 1000", r["state"], env)
        self.assertIn("1500", r["reply"])
        self.assertIn("2 of 3", r["reply"])
        r = say("every 3 marks = 1 day, divided by 30, no cap", r["state"], env)
        self.assertIn("3 of 3", r["reply"])
        r = say("a different gross for each person", r["state"], env)
        self.assertEqual(r["state"]["phase"], "review")
        self.assertIn("Salary structure", r["reply"])
        self.assertIn("Attendance deduction rule", r["reply"])
        for hr_step in ("Industry", "Country", "Locations", "Holiday calendar", "Working hours", "Leave policy"):
            self.assertNotIn(hr_step, r["reply"], hr_step)
        done = say("Yes, set everything up", r["state"], env)
        self.assertTrue(done["done"])
        a = applied[0]
        self.assertEqual((a["structure_name"], a["basic_pct"], a["rule_marks"], a["rule_divisor"], a["rule_cap"]), ("Standard", "60", "3", "30", "0"))
        for hr_key in ("country", "industry", "locations", "weekly_off", "holidays", "shift_name", "leave_casual"):
            self.assertNotIn(hr_key, a, hr_key)

    def test_the_standard_rule_is_one_tap_and_the_numbers_are_checked(self):
        env = self.env()
        r = self.start(env)
        r["state"]["idx"] = 1
        self.assertEqual([o["value"] for o in sc.turn("back", {**r["state"], "idx": 2}, env)["choices"]["options"]], ["every 3 marks, divided by 30, no cap"])
        bad = say("every 99 marks, divided by 30", r["state"], env)
        self.assertIn("between 1 and 31", bad["reply"])
        vague = say("deduct something", r["state"], env)
        self.assertIn("Give both numbers", vague["reply"])
        capped = sc._parse_rules("every 4 marks = 1 day, divided by 26, cap 2000")[0]
        self.assertEqual(capped, {"rule_marks": "4", "rule_divisor": "26", "rule_cap": "2000"})

    def test_an_hr_chat_never_reaches_payroll_questions(self):
        self.assertNotIn("structure", sc.STEPS)
        self.assertNotIn("rules", sc.STEPS)
        r = say("start", None, make_env())
        self.assertEqual(r["state"]["flow"], "")


class IntentTests(unittest.TestCase):
    def test_a_setup_question_on_an_hr_page_starts_the_agent_instead_of_a_text_answer(self):
        q = "Which industry should I choose for my company, and what will it pre-load? Ask me what my company does if you need to."
        self.assertEqual(sc.intent(q, "reckon-hrms/reckon-hrms-hr-studio"), "start industry")
        self.assertEqual(sc.intent("Guide me through setting up payroll step by step for my company.", "reckon-hrms/reckon-hrms-setup"), "start payroll")
        self.assertEqual(sc.intent("Help me set up HR", "reckon-hrms/reckon-hrms-hr-studio"), "start")

    def test_other_questions_and_other_pages_are_left_to_the_normal_answer(self):
        self.assertIsNone(sc.intent("Why can't I create a leave application?", "reckon-hrms/reckon-hrms-hr-studio"))
        self.assertIsNone(sc.intent("How do I set up a sales invoice?", "accounts-saas/sales-invoice"))
        self.assertIsNone(sc.intent("", ""))

    def test_the_agent_can_start_at_the_industry_question(self):
        r = sc.turn("start industry", None, make_env())
        self.assertEqual(r["state"]["idx"], sc.STEPS.index("industry"))
        self.assertIn("What does your company do", r["reply"])

    def test_a_description_of_the_business_picks_the_industry(self):
        env = make_env()
        env["industries"] = [{"key": "it_software", "label": "IT / Software"}, {"key": "manufacturing_rmg_textile", "label": "Manufacturing / RMG / Textile"},
                             {"key": "healthcare", "label": "Healthcare"}]
        r = sc.turn("start industry", None, env)
        r = sc.turn("we make garments in a factory near Gazipur", r["state"], env)
        self.assertEqual(r["state"]["answers"]["industry"], "manufacturing_rmg_textile")
        self.assertIn("Manufacturing / RMG / Textile", r["reply"])
        r2 = sc.turn("start industry", None, env)
        r2 = sc.turn("a small clinic", r2["state"], env)
        self.assertEqual(r2["state"]["answers"]["industry"], "healthcare")
        r3 = sc.turn("start industry", None, env)
        r3 = sc.turn("we do many things", r3["state"], env)
        self.assertNotIn("industry", r3["state"]["answers"])


class NowTests(unittest.TestCase):
    """Each question shows what the company already has and the page that edits it."""

    def env(self):
        env = make_env()
        env["current"] = {"country": "Bangladesh", "language": "bn", "locations": "Head Office, Dhaka Factory", "weekly_off": ["Friday"],
                          "shift_name": "General", "shift_start": "09:00", "shift_end": "17:30", "leave_casual": "10", "leave_sick": "14",
                          "structure_name": "Standard Structure", "basic_pct": "60"}
        env["current_industry"] = "healthcare"
        return env

    def ask(self, key):
        r = say("start " + key, None, self.env())
        return r

    def test_existing_data_is_shown_with_its_edit_page(self):
        self.assertIn("Now: Head Office, Dhaka Factory. Skip to keep it, or edit it in Branch.", self.ask("locations")["reply"])
        self.assertIn("edit it in Shift Type", self.ask("shift")["reply"])
        self.assertIn("Now: Casual 10, Sick 14", self.ask("leave")["reply"])
        self.assertIn("edit it in Salary Structure", say("start payroll", None, self.env())["reply"])
        self.assertIn("Now: Friday", self.ask("weekly_off")["reply"])

    def test_nothing_is_shown_when_nothing_exists_yet(self):
        r = say("start locations", None, make_env())
        self.assertNotIn("Now:", r["reply"])

    def test_radio_buttons_and_checkboxes_open_with_the_current_choice(self):
        lang = self.ask("language")["choices"]["options"]
        self.assertEqual([o["checked"] for o in lang], [False, True])
        ind = self.ask("industry")["choices"]["options"]
        self.assertEqual([o["label"] for o in ind if o["checked"]], ["Healthcare"])
        days = self.ask("weekly_off")["choices"]["options"]
        self.assertEqual([o["value"] for o in days if o["checked"]], ["Friday"])


class StructureNameTests(unittest.TestCase):
    def test_a_name_written_first_is_the_structure_name(self):
        self.assertEqual(sc._parse_structure("Standard, basic 50, house rent 10")[0]["structure_name"], "Standard")
        self.assertEqual(sc._parse_structure("Office Staff basic 60")[0]["structure_name"], "Office Staff")

    def test_without_a_name_the_existing_structure_name_is_kept_so_it_is_not_added_twice(self):
        self.assertEqual(sc._parse_structure("basic 50", "Standard")[0]["structure_name"], "Standard")
        self.assertEqual(sc._parse_structure("basic 50")[0]["structure_name"], "Standard Structure")

    def test_the_existing_name_matches_an_existing_structure_in_the_plan(self):
        env = make_env()
        env["current"] = {"structure_name": "Standard"}
        r = sc.turn("start payroll", None, env)
        r = sc.turn("basic 50, house rent 10", r["state"], env)
        self.assertEqual(r["state"]["answers"]["structure_name"], "Standard")


class HrFirstChatTests(unittest.TestCase):
    def env(self, pending):
        env = make_env()
        env["current"] = {}
        env["hr_pending"] = pending
        return env

    def test_payroll_asks_nothing_while_hr_is_unfinished_and_offers_the_hr_setup(self):
        r = say("start payroll", None, self.env(["Employees", "Attendance and working hours"]))
        self.assertIn("Payroll needs HR set up first", r["reply"])
        self.assertIn("Employees; Attendance and working hours", r["reply"])
        self.assertNotIn("1 of 3", r["reply"])
        self.assertEqual([o["value"] for o in r["choices"]["options"]], ["start"])
        self.assertEqual(r["state"]["flow"], "")

    def test_choosing_the_hr_setup_starts_the_hr_questions(self):
        env = self.env(["Employees"])
        r = say("start payroll", None, env)
        r = say("start", r["state"], env)
        self.assertIn("Which country", r["reply"])
        self.assertEqual(r["state"]["flow"], "")

    def test_payroll_questions_start_once_hr_is_done(self):
        r = say("start payroll", None, self.env([]))
        self.assertIn("1 of 3", r["reply"])
        self.assertEqual(r["state"]["flow"], "payroll")


class PayrollPageBlockTests(unittest.TestCase):
    def test_the_payroll_tab_shows_a_finish_hr_first_prompt_and_disables_payroll_actions(self):
        from pathlib import Path

        js = (Path(__file__).resolve().parents[1] / "reckon_hrms" / "public" / "js" / "reckon_guided_setup.js").read_text(encoding="utf-8")
        for needle in ("Finish HR setup first", "data-hr-first", "data.hr_pending", "!data.hr_ready"):
            self.assertIn(needle, js)


class PayrollInterviewPageTests(unittest.TestCase):
    """The payroll tab has the same helpful pieces as HR Studio's guided setup: an Ask AI card and a pre-filled interview."""

    def setUp(self):
        from pathlib import Path

        self.js = (Path(__file__).resolve().parents[1] / "reckon_hrms" / "public" / "js" / "reckon_guided_setup.js").read_text(encoding="utf-8")

    def test_the_payroll_tab_has_the_ask_ai_card_and_an_interview_that_opens_when_hr_is_done(self):
        for needle in ('interview(root, "payroll", $())', "data.hr_ready"):
            self.assertIn(needle, self.js)

    def test_both_studios_put_the_setup_interview_first_and_use_the_same_ask_ai_card(self):
        hr = self.js[self.js.index("window.ReckonGuidedSetup = function"):]
        self.assertLess(hr.index("data-ask-main"), hr.index("data-interview"))
        self.assertLess(hr.index("data-interview"), hr.index("data-review"))
        self.assertLess(hr.index("data-review"), hr.index("data-more"))
        payroll = self.js[self.js.index("function payrollPanel"): self.js.index("window.ReckonGuidedSetup = function")]
        self.assertLess(payroll.index("data-ask>"), payroll.index("data-interview"))
        self.assertLess(payroll.index("data-interview"), payroll.index("data-groups"))
        # the same heading and button wording in both
        self.assertEqual(payroll.count("Guided setup with Ask AI"), 1)
        self.assertIn("✦ Ask AI to set it up for me", payroll)
        self.assertNotIn("Ask AI to set up payroll", self.js)

    def test_the_payroll_button_always_starts_the_chat_so_the_agent_explains_what_comes_first(self):
        self.assertIn('root.on("click", "[data-ask]", () => window.ReckonStudioAsk("payroll"));', self.js)

    def test_each_studio_asks_only_its_own_questions(self):
        self.assertIn('(studio === "payroll" ? x.studio === "payroll" : x.studio !== "payroll")', self.js)
        self.assertIn("PAYROLL_KEYS", self.js)

    def test_payroll_sends_only_payroll_answers_so_no_hr_setting_changes(self):
        start = self.js.index("const PAYROLL_KEYS")
        block = self.js[start: start + 600]
        self.assertIn("rule_marks", block)
        self.assertIn("structure_name", block)
        self.assertNotIn("weekly_off", block.split(":")[0])

    def test_the_rule_question_has_a_one_tap_standard_and_an_edit_link(self):
        self.assertIn("data-standard-rule", self.js)
        self.assertIn('rules: ["Company", LINKS.company]', self.js)


class SmartReplyTests(unittest.TestCase):
    """With the AI on, the agent understands sentences and answers questions; the plain reader still checks every answer."""

    def env(self, ai_text=None, ai_answer=None):
        env = make_env()
        env["current"] = {}
        if ai_text:
            env["ai_text"] = ai_text
        if ai_answer:
            env["ai_answer"] = ai_answer
        return env

    def at(self, key, env):
        r = say("start", None, env)
        r["state"]["idx"] = sc.STEPS.index(key)
        return r

    def test_a_sentence_for_a_list_is_rewritten_by_the_ai_then_read_by_the_normal_reader(self):
        seen = []

        def ai_text(key, text, fmt):
            seen.append((key, fmt))
            return "Head Office, Dhaka Factory, Khulna Depot"

        env = self.env(ai_text)
        r = self.at("locations", env)
        r = say("we have our head office, a factory in Dhaka and a depot in Khulna", {**r["state"], "idx": sc.STEPS.index("locations")}, env)
        self.assertEqual(r["state"]["answers"]["locations"], "Head Office, Dhaka Factory, Khulna Depot")
        self.assertEqual(seen[0][0], "locations")
        self.assertIn("Head Office", seen[0][1])

    def test_a_plain_list_never_goes_to_the_ai(self):
        called = []
        env = self.env(lambda *a: called.append(a))
        r = self.at("locations", env)
        say("Head Office, Dhaka Factory", {**r["state"], "idx": sc.STEPS.index("locations")}, env)
        self.assertEqual(called, [])

    def test_a_reply_the_plain_reader_cannot_use_is_rewritten_then_checked_again(self):
        env = self.env(lambda key, text, fmt: "casual 10, sick 14")
        r = self.at("leave", env)
        r = say("ten days of casual and fourteen sick leave a year", {**r["state"], "idx": sc.STEPS.index("leave")}, env)
        self.assertEqual((r["state"]["answers"]["leave_casual"], r["state"]["answers"]["leave_sick"]), ("10", "14"))

    def test_the_ai_cannot_put_a_value_in_that_the_reader_rejects(self):
        env = self.env(lambda key, text, fmt: "every 99 marks, divided by 30")
        r = say("start payroll", None, env)
        r = say("basic 60", r["state"], env)
        self.assertEqual(r["state"]["idx"], 1)  # now on the deduction rule
        r = say("something vague", r["state"], env)
        self.assertNotIn("rule_marks", r["state"]["answers"])
        self.assertEqual(r["state"]["idx"], 1)
        self.assertIn("Give both numbers", r["reply"])

    def test_the_ai_saying_none_leaves_the_normal_error(self):
        env = self.env(lambda key, text, fmt: None)
        r = self.at("leave", env)
        r = say("many days", {**r["state"], "idx": sc.STEPS.index("leave")}, env)
        self.assertIn("Give the days per year", r["reply"])
        self.assertEqual(r["state"]["idx"], sc.STEPS.index("leave"))

    def test_a_question_in_the_middle_is_answered_and_the_question_is_asked_again(self):
        env = self.env(ai_answer=lambda q, step: f"House rent allowance is part of pay. ({step})")
        r = self.at("weekly_off", env)
        r = say("what is the usual weekly off in Bangladesh?", {**r["state"], "idx": sc.STEPS.index("weekly_off")}, env)
        self.assertIn("House rent allowance is part of pay. (Weekly off)", r["reply"])
        self.assertIn("Back to the setup", r["reply"])
        self.assertIn("weekly off", r["reply"].lower())
        self.assertEqual(r["state"]["idx"], sc.STEPS.index("weekly_off"))
        self.assertNotIn("weekly_off", r["state"]["answers"])

    def test_without_ai_a_question_is_read_as_an_answer_attempt_as_before(self):
        env = self.env()
        r = self.at("leave", env)
        r = say("how many days?", {**r["state"], "idx": sc.STEPS.index("leave")}, env)
        self.assertIn("Give the days per year", r["reply"])


class StudioStartTests(unittest.TestCase):
    def test_the_payroll_studio_starts_the_payroll_flow_not_the_hr_one(self):
        from pathlib import Path

        js = (Path(__file__).resolve().parents[1] / "reckon_hrms" / "public" / "js" / "reckon_guided_setup.js").read_text(encoding="utf-8")
        self.assertIn('window.aura.start_agent("hrms_setup", studio === "payroll" ? "start payroll" : "start")', js)


class AiTimeBudgetTests(unittest.TestCase):
    """The AI must never hold the chat for a minute: its calls are capped, and a failure falls back to the plain reader."""

    def test_the_agents_ai_calls_are_capped_in_seconds(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[1] / "reckon_hrms"
        setup = (root / "api" / "ai_setup.py").read_text(encoding="utf-8")
        agent = (root / "ai_agent.py").read_text(encoding="utf-8")
        self.assertIn("timeout: int = 30", setup)
        self.assertIn("timeout=timeout", setup)
        self.assertIn("timeout=40", agent)

    def test_a_failing_or_silent_ai_leaves_the_plain_behaviour(self):
        env = make_env()
        env["current"] = {}
        env["ai_text"] = lambda key, text, fmt: None
        r = say("start", None, env)
        r = say("we have our head office and a factory in Dhaka and one depot", {**r["state"], "idx": sc.STEPS.index("locations")}, env)
        # the plain reader keeps the sentence as the one name it can read, exactly as before
        self.assertIn("locations", r["state"]["answers"])


class GrossAdviceTests(unittest.TestCase):
    def test_a_different_gross_for_each_person_gets_the_one_structure_advice_and_the_interview_carries_on(self):
        from reckon_hrms import setup_chat

        env = {"company": "Acme", "countries": [], "industries": [], "year": 2026, "current": {}, "steps": None,
               "build_plan": lambda a: {"steps": []}, "apply": lambda a: {"results": [], "done": 0, "failed": 0}}
        first = setup_chat.turn("start payroll", None, env)
        out = setup_chat.turn("Every employee has a different gross salary", first["state"], env)
        self.assertIn("Each person's gross salary", out["reply"])
        self.assertIn("Back to the setup", out["reply"])
        self.assertEqual(out["state"]["idx"], first["state"]["idx"])

    def test_the_deduction_rule_wording_is_not_mistaken_for_it(self):
        from reckon_hrms import setup_chat

        self.assertIsNone(setup_chat.GROSS_HELP.search("every 3 late marks = 1 day, pay / 30"))


class PayAmountsStepTests(unittest.TestCase):
    def test_the_last_payroll_question_is_same_or_different_gross_and_changes_the_closing_advice(self):
        from reckon_hrms import setup_chat

        self.assertEqual(setup_chat.PAYROLL_STEPS[-1], "pay_amounts")
        env = {"company": "Acme", "steps": setup_chat.PAYROLL_STEPS, "year": 2026}
        value, error, _ = setup_chat._read("pay_amounts", "a different gross for each person", env, {})
        self.assertEqual(value, {"pay_mode": "different"})
        value, error, _ = setup_chat._read("pay_amounts", "The same gross for everyone", env, {})
        self.assertEqual(value, {"pay_mode": "same"})
        value, error, _ = setup_chat._read("pay_amounts", "banana", env, {})
        self.assertIsNone(value)
        self.assertIn("Please choose", error)
        self.assertIn("Each person's gross salary", setup_chat._pay_next("different"))
        self.assertNotIn("Each person's gross salary", setup_chat._pay_next("same"))
        self.assertIn("same gross", setup_chat._pay_next(None))
