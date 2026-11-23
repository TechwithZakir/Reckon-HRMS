"""The setup review after setup: each step, what it holds, and where to review or edit it (no Frappe)."""

import unittest

from reckon_hrms import setup_review as sr


def facts(**over):
    base = {"company": "Acme", "user": "a@x.test", "country": "Bangladesh", "language": "English", "industry_label": "IT / Software",
            "branches": 2, "departments": 7, "designations": 9, "holiday_list": "Holidays 2026 - Acme", "weekly_off": ["Friday"],
            "named_holidays": 13, "shifts": 1, "leave_policies": 1, "structures": 1, "assignments": 0, "components": 9}
    base.update(over)
    return base


class ReviewTests(unittest.TestCase):
    def test_every_hr_step_links_to_its_own_list_or_record(self):
        rows = {r["key"]: r for r in sr.rows(facts())}
        self.assertEqual(rows["holidays"]["doctype"], "Holiday List")
        self.assertEqual(rows["holidays"]["name"], "Holidays 2026 - Acme")
        self.assertEqual(rows["country"]["name"], "Acme")
        self.assertEqual((rows["locations"]["doctype"], rows["locations"]["name"]), ("Branch", None))
        self.assertEqual(rows["shift"]["doctype"], "Shift Type")
        self.assertEqual(rows["leave"]["doctype"], "Leave Policy")
        self.assertEqual(rows["holidays"]["detail"], "Weekly off: Friday; 13 public holidays")
        self.assertEqual(rows["locations"]["detail"], "2 branches")

    def test_a_finished_setup_is_recognised_and_an_empty_one_is_not(self):
        self.assertTrue(sr.finished(sr.rows(facts())))
        empty = facts(country="", language="", industry_label="", branches=0, departments=0, designations=0, holiday_list="", weekly_off=[],
                      named_holidays=0, shifts=0, leave_policies=0)
        self.assertFalse(sr.finished(sr.rows(empty)))
        no_industry = facts(industry_label="")
        self.assertFalse(sr.finished(sr.rows(no_industry)))

    def test_a_step_with_nothing_is_not_done_and_names_the_chat_question_that_fills_it(self):
        rows = {r["key"]: r for r in sr.rows(facts(shifts=0, leave_policies=0, branches=0))}
        for key, chat in (("shift", "shift"), ("leave", "leave"), ("locations", "locations")):
            self.assertFalse(rows[key]["done"])
            self.assertEqual(rows[key]["chat"], chat)
        self.assertEqual(rows["shift"]["detail"], "0 shifts")

    def test_payroll_shows_pay_items_structure_and_assignments(self):
        rows = sr.rows(facts(), "payroll")
        self.assertEqual([r["key"] for r in rows], ["industry", "components", "structure", "assignments"])
        by = {r["key"]: r for r in rows}
        self.assertEqual(by["structure"]["doctype"], "Salary Structure")
        self.assertEqual(by["assignments"]["doctype"], "Salary Structure Assignment")
        self.assertFalse(by["assignments"]["done"])
        self.assertIsNone(by["assignments"]["chat"])  # giving people a structure is done in Salary rules, not in the chat

    def test_singular_and_plural_counts(self):
        rows = {r["key"]: r for r in sr.rows(facts(branches=1, departments=1))}
        self.assertEqual(rows["locations"]["detail"], "1 branch")
        self.assertEqual(rows["departments"]["detail"], "1 department")


if __name__ == "__main__":
    unittest.main()


class ReadBackTests(unittest.TestCase):
    """What the company already has comes back as interview answers, so the questions open pre-filled."""

    def test_a_shift_comes_back_without_the_company_suffix_and_with_hh_mm_times(self):
        self.assertEqual(sr.shift_answers("General Shift - ACME", "09:00:00", "17:30:00", 10, "ACME"),
                         {"shift_name": "General Shift", "shift_start": "09:00", "shift_end": "17:30", "late_grace": "10"})
        self.assertNotIn("late_grace", sr.shift_answers("Day", "9:00:00", "17:00:00", 0))

    def test_a_leave_policy_comes_back_as_days_per_type(self):
        rows = [{"leave_type": "Casual Leave", "annual_allocation": 10.0}, {"leave_type": "Sick Leave", "annual_allocation": 14.0},
                {"leave_type": "Compensatory Off", "annual_allocation": 3.0}, {"leave_type": "Earned Leave", "annual_allocation": 0}]
        self.assertEqual(sr.leave_answers(rows), {"leave_casual": "10", "leave_sick": "14"})

    def test_a_structure_gives_back_percents_only_when_they_are_plain_percents_of_the_gross(self):
        earnings = [
            {"salary_component": "Basic Salary", "amount_based_on_formula": 1, "formula": "base * 0.6", "amount": 0},
            {"salary_component": "House Rent Allowance", "amount_based_on_formula": 1, "formula": "BASIC * 0.5", "amount": 0},
            {"salary_component": "Medical Allowance", "amount_based_on_formula": 0, "formula": "", "amount": 1500.0},
            {"salary_component": "Conveyance Allowance", "amount_based_on_formula": 0, "formula": "", "amount": 1000.0},
        ]
        out = sr.structure_answers("Standard Structure - Acme", "Acme", earnings)
        self.assertEqual(out, {"structure_name": "Standard Structure", "basic_pct": "60", "medical_amount": "1500", "conveyance_amount": "1000"})
        self.assertNotIn("hra_pct", out)  # "50% of Basic" is not a percent of the gross: shown on the page, not guessed here

    def test_holidays_come_back_as_the_calendar_flag_or_the_named_list(self):
        named = [{"date": "2026-03-26", "name": "Independence Day"}]
        self.assertEqual(sr.holiday_answers(True, ["Friday"], named), {"weekly_off": ["Friday"], "holidays_country": "1"})
        self.assertEqual(sr.holiday_answers(False, ["Friday", "Saturday"], named),
                         {"weekly_off": ["Friday", "Saturday"], "holidays": "2026-03-26 Independence Day"})
        self.assertEqual(sr.holiday_answers(False, [], []), {"weekly_off": []})

    def test_what_is_read_back_goes_through_the_same_clean_up_as_typed_answers(self):
        from reckon_hrms import setup_plan as sp

        raw = {**sr.shift_answers("General", "09:00:00", "17:30:00", 10), **sr.leave_answers([{"leave_type": "Casual Leave", "annual_allocation": 10}]),
               **sr.structure_answers("Std - Acme", "Acme", [{"salary_component": "Basic Salary", "amount_based_on_formula": 1, "formula": "base * 0.6"}])}
        a = sp.normalize_answers(raw, 2026)
        self.assertEqual(a["shift"], {"name": "General", "start": "09:00:00", "end": "17:30:00", "grace": 10})
        self.assertEqual(a["leave"], {"Casual Leave": 10.0})
        self.assertEqual(a["structure"]["basic_pct"], 60.0)


class PayrollGroupsTests(unittest.TestCase):
    def facts(self, **over):
        base = {"company": "Acme", "employees": 12, "holiday_list": "Holidays 2026 - Acme", "shifts": 1, "leave_policies": 1, "payable_account": "Payroll Payable - A",
                "components": 9, "structures": 1, "active": 12, "assigned": 12, "rules": {"marks_per_day": 3, "divisor": 30, "cap": 0.0},
                "last_run": {"name": "HR-PRUN-1", "status": "Paid"}}
        base.update(over)
        return base

    def rows(self, **over):
        groups = sr.payroll_groups(self.facts(**over))
        return groups, {r["key"]: r for g in groups for r in g["rows"]}

    def test_hr_owned_steps_are_shown_as_status_with_a_link_and_never_as_questions(self):
        groups, rows = self.rows(employees=0, holiday_list="", shifts=0, leave_policies=0)
        self.assertEqual(groups[0]["title"], "Already handled in HR Studio")
        self.assertEqual([r["key"] for r in groups[0]["rows"]], ["employees", "holidays", "attendance", "leave"])
        for key in ("employees", "holidays", "attendance", "leave"):
            self.assertFalse(rows[key]["done"])
            self.assertEqual(rows[key]["actions"][0]["kind"], "hr")
        done_groups, done_rows = self.rows()
        self.assertEqual(done_rows["holidays"]["actions"][0], {"kind": "open", "doctype": "Holiday List", "name": "Holidays 2026 - Acme", "label": "Review / edit"})

    def test_the_payroll_steps_follow_the_order_hrms_needs(self):
        groups, _rows = self.rows()
        self.assertEqual([r["key"] for r in groups[1]["rows"]], ["payable", "components", "structure", "rules", "assignments", "run"])

    def test_each_missing_payroll_step_offers_the_right_action(self):
        _g, rows = self.rows(payable_account="", components=0, structures=0, assigned=3)
        self.assertEqual(rows["payable"]["actions"][0]["kind"], "fix")
        self.assertEqual(rows["components"]["actions"][0]["kind"], "hr")
        self.assertEqual(rows["structure"]["actions"][0]["kind"], "agent")
        self.assertEqual(rows["assignments"]["actions"][0], {"kind": "stage", "stage": "salary", "label": "Give structure to people"})
        self.assertFalse(rows["assignments"]["done"])
        self.assertEqual(rows["assignments"]["detail"], "3 of 12 active people have a structure")

    def test_the_deduction_rule_is_always_editable_and_describes_the_values(self):
        _g, rows = self.rows(rules={"marks_per_day": 4, "divisor": 26, "cap": 2000.0})
        self.assertEqual(rows["rules"]["actions"][0]["kind"], "rules")
        self.assertEqual(rows["rules"]["detail"], "Every 4 late or early marks = 1 day, pay / 26, cap 2000")
        _g, rows = self.rows(rules={"marks_per_day": 3, "divisor": 30, "cap": 0.0})
        self.assertTrue(rows["rules"]["detail"].endswith("no cap"))

    def test_the_run_row_shows_the_latest_run_and_nothing_when_there_is_none(self):
        _g, rows = self.rows(last_run=None)
        self.assertEqual(rows["run"]["detail"], "No run yet")
        self.assertFalse(rows["run"]["done"])
        _g, rows = self.rows(last_run={"name": "HR-PRUN-2", "status": "Draft"})
        self.assertEqual(rows["run"]["detail"], "Latest run HR-PRUN-2: Draft")


class HrFirstTests(unittest.TestCase):
    def groups(self, **over):
        base = {"company": "Acme", "employees": 12, "holiday_list": "H", "shifts": 1, "leave_policies": 1, "payable_account": "P", "components": 9,
                "structures": 1, "active": 12, "assigned": 12, "rules": {"marks_per_day": 3, "divisor": 30, "cap": 0.0}, "last_run": None}
        base.update(over)
        return sr.payroll_groups(base)

    def test_nothing_blocks_payroll_when_hr_is_done(self):
        self.assertEqual(sr.hr_pending(self.groups()), [])

    def test_each_unfinished_hr_step_is_listed_with_where_to_fix_it(self):
        pending = sr.hr_pending(self.groups(employees=0, shifts=0))
        self.assertEqual([p["label"] for p in pending], ["Employees", "Attendance and working hours"])
        self.assertTrue(all(p["actions"][0]["kind"] == "hr" for p in pending))

    def test_payroll_steps_alone_never_count_as_hr_pending(self):
        self.assertEqual(sr.hr_pending(self.groups(payable_account="", components=0, structures=0)), [])


class IndustryRowTests(unittest.TestCase):
    def test_the_industry_is_a_template_with_no_page_to_open(self):
        facts = {"company": "Acme", "user": "u", "country": "BD", "language": "English", "industry_label": "IT / Software", "branches": 1, "departments": 1,
                 "designations": 1, "holiday_list": "H", "weekly_off": [], "named_holidays": 0, "shifts": 1, "leave_policies": 1}
        row = next(r for r in sr.rows(facts) if r["key"] == "industry")
        self.assertEqual(row["label"], "Industry template")
        self.assertIsNone(row["doctype"])
        self.assertIsNone(row["name"])
        self.assertEqual(row["detail"], "IT / Software")

    def test_the_page_offers_a_picker_for_it_not_an_open_link(self):
        from pathlib import Path

        js = (Path(__file__).resolve().parents[1] / "reckon_hrms" / "public" / "js" / "reckon_guided_setup.js").read_text(encoding="utf-8")
        self.assertIn("data-pick-industry", js)
        self.assertIn('x.key === "industry"', js)
