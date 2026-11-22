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
