import unittest
from datetime import date

from reckon_hrms import importer

KNOWN = {
    "department": {"Production", "Accounts"},
    "designation": {"Operator", "Supervisor"},
    "branch": {"Gazipur Factory"},
    "grade": {"Worker"},
    "employment_type": {"Permanent"},
}


def row(**kw):
    base = {"first_name": "Rahim", "last_name": "Hossain", "gender": "Male", "date_of_birth": "1990-05-01", "date_of_joining": "2026-07-01",
            "department": "Production", "designation": "Operator", "cell_number": "01712345678"}
    base.update(kw)
    return base


class ImporterTests(unittest.TestCase):
    def test_template_has_headers(self):
        self.assertTrue(importer.template_csv().startswith("first_name,last_name,gender"))

    def test_good_row_is_ready(self):
        result = importer.check_rows([row()], KNOWN, today=date(2026, 11, 8))
        self.assertEqual((result["read"], result["ready"], result["to_fix"]), (1, 1, 0))

    def test_misspelt_department_gets_a_suggestion(self):
        result = importer.check_rows([row(department="Prodction")], KNOWN, today=date(2026, 11, 8))
        self.assertEqual(result["to_fix"], 1)
        error = result["errors"][0]
        self.assertEqual(error["row"], 2)
        self.assertEqual(error["suggestion"], "Production")
        self.assertIn("Did you mean 'Production'?", error["message"])

    def test_missing_and_bad_values_are_reported(self):
        bad = row(first_name="", date_of_joining="soon", cell_number="12345", gender="Robot")
        result = importer.check_rows([bad], KNOWN, today=date(2026, 11, 8))
        fields = {f for e in result["errors"] for f in e["fields"]}
        self.assertTrue({"first_name", "date_of_joining", "cell_number", "gender"} <= fields)

    def test_future_joining_date_is_refused(self):
        result = importer.check_rows([row(date_of_joining="2027-01-01")], KNOWN, today=date(2026, 11, 8))
        self.assertEqual(result["errors"][0]["field"], "date_of_joining")

    def test_dates_in_common_formats_are_accepted(self):
        self.assertEqual(importer.parse_date("01-07-2026"), date(2026, 7, 1))
        self.assertIsNone(importer.parse_date("31/31/2026"))

    def test_counts_and_error_cap(self):
        many = [row(department="Nope") for _ in range(120)]
        result = importer.check_rows(many, KNOWN, today=date(2026, 11, 8))
        self.assertEqual((result["read"], result["to_fix"]), (120, 120))
        self.assertEqual(len(result["errors"]), 50)


class GrossSalaryTests(unittest.TestCase):
    TODAY = date(2026, 11, 8)

    def check(self, known_extra, **kw):
        return importer.check_rows([row(**kw)], {**KNOWN, **known_extra}, today=self.TODAY)

    def test_amounts_read_with_commas_and_reject_nonsense(self):
        self.assertEqual(importer.parse_amount("45,000"), 45000.0)
        self.assertEqual(importer.parse_amount("45000.505"), 45000.5)
        for bad in ("", "abc", "0", "-5", "99999999999"):
            self.assertIsNone(importer.parse_amount(bad))

    def test_the_template_has_the_pay_columns(self):
        self.assertIn("gross_salary,salary_structure", importer.template_csv())

    def test_no_gross_is_fine(self):
        self.assertEqual(self.check({})["ready"], 1)

    def test_a_gross_uses_the_only_structure_when_there_is_one(self):
        self.assertEqual(self.check({"salary_structure": {"Std"}, "structure_default": {"Std"}}, gross_salary="45,000")["ready"], 1)

    def test_a_gross_needs_a_named_structure_when_there_are_several_or_none(self):
        out = self.check({"salary_structure": {"A", "B"}, "structure_default": set()}, gross_salary="45000")
        self.assertEqual(out["errors"][0]["field"], "salary_structure")
        ok = self.check({"salary_structure": {"A", "B"}, "structure_default": set()}, gross_salary="45000", salary_structure="B")
        self.assertEqual(ok["ready"], 1)

    def test_an_unknown_structure_or_bad_gross_or_orphan_structure_is_reported(self):
        known = {"salary_structure": {"Staff"}, "structure_default": set()}
        self.assertIn("Did you mean 'Staff'?", self.check(known, gross_salary="1000", salary_structure="Staf")["errors"][0]["message"])
        self.assertEqual(self.check(known, gross_salary="lots")["errors"][0]["field"], "gross_salary")
        self.assertEqual(self.check(known, salary_structure="Staff")["errors"][0]["field"], "gross_salary")


if __name__ == "__main__":
    unittest.main()
