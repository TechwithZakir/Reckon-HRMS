"""Unit tests for the Bangladeshi SME starter data."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from reckon_hrms.defaults import (  # noqa: E402
    DEPARTMENTS, DESIGNATIONS, LEAVE_TYPES, SALARY_COMPONENTS, SHIFT_TYPES,
)


class StarterDataTests(unittest.TestCase):
    def test_names_are_unique_within_each_list(self):
        self.assertEqual(len(DEPARTMENTS), len(set(DEPARTMENTS)))
        self.assertEqual(len(DESIGNATIONS), len(set(DESIGNATIONS)))
        for rows in (LEAVE_TYPES, SALARY_COMPONENTS, SHIFT_TYPES):
            names = [row["name"] for row in rows]
            self.assertEqual(len(names), len(set(names)))

    def test_salary_abbreviations_are_unique_and_short(self):
        abbrs = [row["abbr"] for row in SALARY_COMPONENTS]
        self.assertEqual(len(abbrs), len(set(abbrs)))
        self.assertTrue(all(len(a) <= 5 for a in abbrs))

    def test_salary_component_types_are_valid(self):
        self.assertTrue(all(row["type"] in ("Earning", "Deduction") for row in SALARY_COMPONENTS))

    def test_bangladesh_statutory_leave_minimums(self):
        leave = {row["name"]: row["max_leaves_allowed"] for row in LEAVE_TYPES}
        self.assertEqual(leave["Casual Leave"], 10)
        self.assertEqual(leave["Sick Leave"], 14)
        self.assertEqual(leave["Festival Leave"], 11)

    def test_standard_working_day(self):
        self.assertEqual(SHIFT_TYPES[0]["start_time"], "09:00:00")
        self.assertEqual(SHIFT_TYPES[0]["end_time"], "17:00:00")


if __name__ == "__main__":
    unittest.main()
