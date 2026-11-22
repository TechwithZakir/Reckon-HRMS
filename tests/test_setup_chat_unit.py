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
                      "General Shift 09:00 to 17:30, grace 10 minutes", "casual 10, sick 14, earned 18, maternity 112",
                      "basic 60, house rent 20, medical 1500, conveyance 1000"):
            r = say(reply, r["state"], env)
        return r

    def test_the_last_answer_shows_the_plan_and_waits_for_a_yes(self):
        applied = []
        r = self.run_all(make_env(applied))
        self.assertIn("Here is your setup plan", r["reply"])
        self.assertIn("Nothing has been created yet", r["reply"])
        self.assertIn("Yes, set everything up", r["replies"])
        self.assertEqual(applied, [])
        a = r["state"]["answers"]
        self.assertEqual((a["shift_start"], a["shift_end"], a["late_grace"]), ("09:00", "17:30", "10"))
        self.assertEqual((a["leave_casual"], a["leave_maternity"]), ("10", "112"))
        self.assertEqual((a["basic_pct"], a["hra_pct"], a["medical_amount"], a["conveyance_amount"]), ("60", "20", "1500", "1000"))
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
        r = say("start", None, env)
        r["state"]["answers"].update(structure_name="Std")
        r["state"]["idx"] = sc.STEPS.index("structure")
        r = say("skip", r["state"], env)
        self.assertNotIn("structure_name", r["state"]["answers"])
        self.assertEqual(r["state"]["phase"], "review")
        self.assertNotIn("needs fixing", r["reply"])

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
        self.assertIn("Yes, add them", r["replies"])
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
        self.assertTrue(any("18 public holidays of Bangladesh from the ERPNext holiday calendar" in i for i in item))
        none = sp.build_plan(a, None, "Acme", {"country_holidays": 0})
        self.assertIn("no holiday calendar", next(s for s in none["steps"] if s["key"] == "holidays")["note"])


class IntentTests(unittest.TestCase):
    def test_a_setup_question_on_an_hr_page_starts_the_agent_instead_of_a_text_answer(self):
        q = "Which industry should I choose for my company, and what will it pre-load? Ask me what my company does if you need to."
        self.assertEqual(sc.intent(q, "reckon-hrms/reckon-hrms-hr-studio"), "start industry")
        self.assertEqual(sc.intent("Guide me through setting up HR Studio step by step for my company.", "reckon-hrms/reckon-hrms-setup"), "start")
        self.assertEqual(sc.intent("Help me set up payroll", "reckon-hrms/reckon-hrms-hr-studio"), "start")

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
