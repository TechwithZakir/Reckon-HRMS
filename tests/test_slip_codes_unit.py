"""Unit tests for the two-character component codes (no Frappe)."""

import unittest

from reckon_hrms.slip_codes import short_code, short_codes


class CodeTests(unittest.TestCase):
    def test_first_letters_of_first_two_words(self):
        self.assertEqual(short_code("Basic Salary"), "BS")
        self.assertEqual(short_code("House Rent Allowance"), "HR")
        self.assertEqual(short_code("Provident Fund (Employee)"), "PF")
        self.assertEqual(short_code("Income Tax (TDS)"), "IT")

    def test_stop_words_are_skipped(self):
        self.assertEqual(short_code("Late and Early Deduction"), "LE")

    def test_single_word_uses_two_letters(self):
        self.assertEqual(short_code("Overtime"), "OV")

    def test_codes_are_unique_in_a_list(self):
        codes = short_codes(["Basic Salary", "Bonus Scheme", "Basic Salary Arrears"])
        self.assertEqual(codes["Basic Salary"], "BS")
        self.assertEqual(codes["Bonus Scheme"], "B2")
        self.assertEqual(codes["Basic Salary Arrears"], "B3")
        self.assertEqual(len(set(codes.values())), 3)

    def test_all_codes_are_two_characters(self):
        for name, code in short_codes(["Income Tax (TDS)", "X", "Festival Bonus"]).items():
            self.assertEqual(len(code), 2, name)


if __name__ == "__main__":
    unittest.main()
