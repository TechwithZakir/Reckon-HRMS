"""The setup interview's rules: answers become a plan, and nothing is guessed (no Frappe)."""

import json
import unittest
from pathlib import Path

from reckon_hrms import setup_plan as sp

DATA = json.loads((Path(__file__).resolve().parents[1] / "reckon_hrms" / "benchmarks" / "payroll_benchmark_2026.json").read_text(encoding="utf-8"))
SEG = DATA["segments"]["it_software"]


class ParseTests(unittest.TestCase):
    def test_names_are_trimmed_unique_and_ordered(self):
        self.assertEqual(sp.split_names("Sales, sales ;  Support\n Product ,, "), ["Sales", "Support", "Product"])
        self.assertEqual(sp.split_names(""), [])
        self.assertEqual(len(sp.split_names(",".join(f"D{i}" for i in range(100)))), sp.MAX_LIST)

    def test_holidays_read_in_this_year_only_and_the_rest_are_listed(self):
        text = "2026-03-26 Independence Day\n26/12/2026 - Victory Day\n2025-01-01 Old\nsometime in April Eid\n2026-03-26 Duplicate\n2026-02-30 Bad"
        rows, unread = sp.parse_holidays(text, 2026)
        self.assertEqual([r["date"] for r in rows], ["2026-03-26", "2026-12-26"])
        self.assertEqual(rows[1]["name"], "Victory Day")
        self.assertEqual(len(unread), 3)

    def test_numbers_and_times_outside_range_are_dropped_not_guessed(self):
        a = sp.normalize_answers({"leave_casual": "10", "leave_sick": "-3", "leave_earned": "abc", "shift_name": "Day", "shift_start": "25:00", "shift_end": "17:00"})
        self.assertEqual(a["leave"], {"Casual Leave": 10.0})
        self.assertIsNone(a["shift"])
        self.assertIn("start and an end", a["shift_problem"])

    def test_weekly_off_defaults_to_friday_but_can_be_none(self):
        self.assertEqual(sp.normalize_answers({})["weekly_off"], ["Friday"])
        self.assertEqual(sp.normalize_answers({"weekly_off": ["Friday", "Saturday", "Funday"]})["weekly_off"], ["Friday", "Saturday"])
        self.assertEqual(sp.normalize_answers({"weekly_off": []})["weekly_off"], [])

    def test_ai_holiday_rows_keep_only_well_formed_dates_in_the_year(self):
        rows = [{"date": "2026-04-14", "name": "Pohela Boishakh"}, {"date": "2027-01-01", "name": "x"}, {"date": "bad", "name": "y"}, "junk", {"date": "2026-05-01"}]
        self.assertEqual(sp.parse_ai_holidays(rows, 2026), ["2026-04-14 Pohela Boishakh"])
        self.assertEqual(sp.parse_ai_holidays("not a list", 2026), [])


class PlanTests(unittest.TestCase):
    def plan(self, raw, existing=None):
        return sp.build_plan(sp.normalize_answers(raw), SEG, "Acme", existing)

    def steps(self, plan):
        return {s["key"]: s for s in plan["steps"]}

    def test_an_empty_interview_only_loads_the_industry_and_the_weekly_off(self):
        steps = self.steps(self.plan({}))
        self.assertEqual(steps["industry"]["status"], "ready")
        self.assertEqual(steps["holidays"]["status"], "ready")
        for key in ("country", "language", "locations", "departments", "titles", "shift", "leave", "structure"):
            self.assertEqual(steps[key]["status"], "skipped", key)

    def test_a_full_interview_plans_every_step(self):
        plan = self.plan({"country": "Bangladesh", "language": "bn", "locations": "Head Office, Dhaka Factory", "extra_departments": "Legal", "extra_titles": "Intern", "holidays": "2026-03-26 Independence Day",
                          "shift_name": "General", "shift_start": "09:00", "shift_end": "17:30", "late_grace": "10",
                          "leave_casual": "10", "leave_sick": "14", "structure_name": "Standard", "basic_pct": "60", "hra_pct": "20",
                          "medical_amount": "1500", "conveyance_amount": "1000"})
        steps = self.steps(plan)
        self.assertEqual([k for k, s in steps.items() if s["status"] != "ready"], [])
        self.assertIn("Basic Salary: 60% of gross", steps["structure"]["items"])
        self.assertIn("20% of the gross has no pay item yet", steps["structure"]["note"])
        self.assertIn("late entry after 10 min", steps["shift"]["items"][0])
        self.assertEqual(plan["attention"], 0)
        self.assertEqual(steps["locations"]["items"], ["Head Office", "Dhaka Factory"])
        self.assertEqual(steps["language"]["items"], ["বাংলা (Bangla)"])

    def test_the_interview_opens_with_country_language_and_locations_then_departments(self):
        keys = [q["key"] for q in sp.QUESTIONS]
        self.assertEqual(keys[:4], ["country", "language", "locations", "extra_departments"])
        self.assertEqual(keys[-1], "structure_name")
        self.assertTrue(all(q["studio"] == "both" for q in sp.QUESTIONS))

    def test_weekly_off_is_suggested_by_country_and_never_applied_silently(self):
        self.assertEqual(sp.suggest_weekly_off("Bangladesh"), ["Friday"])
        self.assertEqual(sp.suggest_weekly_off("India"), ["Sunday"])
        self.assertEqual(sp.suggest_weekly_off("Germany"), ["Saturday", "Sunday"])
        self.assertEqual(sp.suggest_weekly_off(None), ["Saturday", "Sunday"])
        self.assertEqual(sp.normalize_answers({"country": "India", "language": "xx"})["language"], "")

    def test_what_the_company_already_has_is_not_added_again(self):
        plan = self.plan({"extra_departments": "Sales, Legal"}, existing={"departments": {"Sales"}})
        self.assertEqual(self.steps(plan)["departments"]["items"], ["Legal", "Sales (already there)"])

    def test_problems_ask_for_attention_instead_of_guessing(self):
        steps = self.steps(self.plan({"structure_name": "S", "basic_pct": "70", "hra_pct": "50", "holidays": "Eid sometime"}))
        self.assertEqual(steps["structure"]["status"], "attention")
        self.assertIn("more than 100%", steps["structure"]["note"])
        self.assertEqual(steps["holidays"]["status"], "attention")
        self.assertEqual(self.steps(self.plan({"structure_name": "S"}))["structure"]["status"], "attention")

    def test_no_industry_skips_that_step_and_amounts_are_never_made_up(self):
        plan = sp.build_plan(sp.normalize_answers({}), None, "Acme")
        self.assertEqual(self.steps(plan)["industry"]["status"], "skipped")
        text = json.dumps(plan)
        for word in ("min", "midpoint", "salary band"):
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()


class NoDuplicateTests(unittest.TestCase):
    """What already exists is never added again: the plan says so before anything runs."""

    def plan(self, raw, existing):
        return sp.build_plan(sp.normalize_answers(raw, 2026), SEG, "Acme", existing)

    def steps(self, plan):
        return {s["key"]: s for s in plan["steps"]}

    def test_names_differing_only_in_case_or_spacing_are_the_same(self):
        self.assertTrue(sp.same("Sales", " sales  "))
        self.assertTrue(sp.same("Head  Office", "head office"))
        self.assertFalse(sp.same("Sales", "Sale"))
        self.assertEqual(sp.missing(["Sales", "Legal", "Data  Science"], {"sales", "data science"}), ["Legal"])

    def test_existing_departments_titles_and_branches_are_listed_as_already_there_and_skipped(self):
        existing = {"departments": {"sales", "Legal"}, "designations": {"Intern"}, "branches": {"Head Office"}}
        steps = self.steps(self.plan({"extra_departments": "Sales, Legal", "extra_titles": "intern", "locations": "head  office"}, existing))
        for key in ("departments", "titles", "locations"):
            self.assertEqual(steps[key]["status"], "skipped", key)
            self.assertIn("Already set up", steps[key]["note"])
        self.assertIn("Sales (already there)", steps["departments"]["items"])

    def test_a_mix_adds_only_the_new_ones_and_still_shows_the_others(self):
        steps = self.steps(self.plan({"extra_departments": "Sales, Legal"}, {"departments": {"Sales"}}))
        self.assertEqual(steps["departments"]["status"], "ready")
        self.assertEqual(steps["departments"]["items"], ["Legal", "Sales (already there)"])

    def test_a_second_shift_with_the_same_name_or_the_same_hours_is_not_added(self):
        raw = {"shift_name": "Day", "shift_start": "09:00", "shift_end": "17:30"}
        same_hours = self.steps(self.plan(raw, {"shifts": [{"name": "General Shift - Acme", "start": "09:00:00", "end": "17:30:00"}]}))["shift"]
        self.assertEqual(same_hours["status"], "skipped")
        self.assertIn("General Shift - Acme", same_hours["note"])
        same_name = self.steps(self.plan(raw, {"shifts": [{"name": "day", "start": "08:00:00", "end": "16:00:00"}]}))["shift"]
        self.assertEqual(same_name["status"], "skipped")
        other = self.steps(self.plan(raw, {"shifts": [{"name": "Night", "start": "20:00:00", "end": "04:00:00"}]}))["shift"]
        self.assertEqual(other["status"], "ready")

    def test_an_existing_leave_policy_is_not_replaced_and_the_note_names_where_to_edit_it(self):
        step = self.steps(self.plan({"leave_casual": "10"}, {"leave_policy": "HR-LPOL-2026-00001"}))["leave"]
        self.assertEqual(step["status"], "skipped")
        self.assertIn("Leave Policy", step["note"])
        self.assertEqual(self.steps(self.plan({"leave_casual": "10"}, {}))["leave"]["status"], "ready")

    def test_a_structure_with_the_same_name_is_skipped_and_a_new_name_warns_about_the_others(self):
        raw = {"structure_name": "Standard", "basic_pct": "60"}
        skipped = self.steps(self.plan(raw, {"structures": ["standard"]}))["structure"]
        self.assertEqual(skipped["status"], "skipped")
        added = self.steps(self.plan(raw, {"structures": ["Reckon BD SME"]}))["structure"]
        self.assertEqual(added["status"], "ready")
        self.assertIn("You already have: Reckon BD SME", added["note"])
