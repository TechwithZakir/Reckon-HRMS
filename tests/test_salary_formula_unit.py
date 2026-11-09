"""Unit tests for the payslip preview's plain-language calculation text (no Frappe)."""

import unittest

from reckon_hrms.salary_formula import describe

LABELS = {"BASIC": "Basic Salary", "HRA": "House Rent Allowance"}


class DescribeTests(unittest.TestCase):
    def test_percent_of_base_salary(self):
        self.assertEqual(describe("base * 0.6", True, LABELS), "60% of base salary")

    def test_percent_of_named_component(self):
        self.assertEqual(describe("BASIC * 0.5", True, LABELS), "50% of Basic Salary")

    def test_fixed_amount_when_not_formula_based(self):
        self.assertEqual(describe("base * 0.6", False, LABELS), "Fixed amount")
        self.assertEqual(describe(None, True, LABELS), "Fixed amount")

    def test_unknown_expression_shows_the_formula(self):
        self.assertEqual(describe("min(base, 50000) * 0.1", True, LABELS), "Formula: min(base, 50000) * 0.1")

    def test_condition_is_appended(self):
        text = describe("base * 0.1", True, LABELS, condition="payment_days > 0")
        self.assertEqual(text, "10% of base salary (only when payment_days > 0)")

    def test_unknown_source_falls_back_to_abbreviation(self):
        self.assertEqual(describe("XYZ * 0.2", True, LABELS), "20% of XYZ")


if __name__ == "__main__":
    unittest.main()
