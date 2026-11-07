"""Framework-free tests for the company condition builder.

Run: python -m unittest discover -s tests
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from reckon_hrms.tenancy import build_company_condition  # noqa: E402


class CompanyConditionTests(unittest.TestCase):
    def test_no_company_matches_nothing(self):
        self.assertEqual(build_company_condition("tabEmployee", []), "1=0")

    def test_single_company(self):
        self.assertEqual(
            build_company_condition("tabEmployee", ["Acme Ltd"]),
            "`tabEmployee`.`company` in ('Acme Ltd')",
        )

    def test_values_are_sorted_and_deduplicated(self):
        self.assertEqual(
            build_company_condition("tabEmployee", ["B Co", "A Co", "B Co"]),
            "`tabEmployee`.`company` in ('A Co', 'B Co')",
        )

    def test_quotes_are_escaped(self):
        self.assertEqual(
            build_company_condition("tabEmployee", ["O'Brien & Sons"]),
            "`tabEmployee`.`company` in ('O\\'Brien & Sons')",
        )

    def test_injection_attempt_stays_inside_string(self):
        condition = build_company_condition("tabEmployee", ["x') or 1=1 -- "])
        self.assertEqual(condition, "`tabEmployee`.`company` in ('x\\') or 1=1 -- ')")


if __name__ == "__main__":
    unittest.main()
