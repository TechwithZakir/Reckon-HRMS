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


if __name__ == "__main__":
    unittest.main()
