"""Unit tests for the late-entry and early-exit deduction rules (no Frappe)."""

import unittest

from reckon_hrms.attendance_deduction import (
    days_deducted,
    deduction_amount,
    marks_for_days,
)


class MarksTests(unittest.TestCase):
    def test_late_and_early_on_the_same_day_is_one_mark(self):
        rows = [{"late_entry": True, "early_exit": True, "status": "Present"}]
        self.assertEqual(marks_for_days(rows), 1)

    def test_absent_days_are_not_marks(self):
        rows = [{"late_entry": True, "status": "Absent"}, {"early_exit": True, "status": "Present"}]
        self.assertEqual(marks_for_days(rows), 1)

    def test_plain_present_day_is_not_a_mark(self):
        self.assertEqual(marks_for_days([{"late_entry": False, "early_exit": False, "status": "Present"}]), 0)

    def test_every_three_marks_is_one_day(self):
        self.assertEqual(days_deducted(2), 0)
        self.assertEqual(days_deducted(3), 1)
        self.assertEqual(days_deducted(8), 2)

    def test_marks_per_day_can_be_changed(self):
        self.assertEqual(days_deducted(4, marks_per_day=2), 2)

    def test_zero_or_negative_group_size_deducts_nothing(self):
        self.assertEqual(days_deducted(9, marks_per_day=0), 0)


class AmountTests(unittest.TestCase):
    def test_one_day_is_base_over_divisor(self):
        self.assertEqual(deduction_amount(60000, 1), 2000.0)

    def test_several_days(self):
        self.assertEqual(deduction_amount(45000, 2), 3000.0)

    def test_cap_limits_the_amount(self):
        self.assertEqual(deduction_amount(60000, 5, cap=5000), 5000.0)

    def test_zero_cap_means_no_cap(self):
        self.assertEqual(deduction_amount(60000, 5, cap=0), 10000.0)

    def test_no_days_or_no_base_is_zero(self):
        self.assertEqual(deduction_amount(60000, 0), 0.0)
        self.assertEqual(deduction_amount(0, 3), 0.0)

    def test_divisor_is_used(self):
        self.assertEqual(deduction_amount(30000, 1, divisor=26), round(30000 / 26, 2))


if __name__ == "__main__":
    unittest.main()
