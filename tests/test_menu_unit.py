"""Unit tests for the left navigation definition (no Frappe)."""

import unittest

from reckon_hrms.menu import ICONS, MENU


def _labels():
    labels = []
    for _group, items in MENU:
        for item in items:
            labels.append(item[2] if item[0] == "Page" else item[1])
    return labels


class MenuTests(unittest.TestCase):
    def test_no_item_appears_twice(self):
        labels = _labels()
        self.assertEqual(len(labels), len(set(labels)), [l for l in labels if labels.count(l) > 1])

    def test_setup_is_first(self):
        self.assertEqual(MENU[0][0], "Setup")

    def test_hr_and_payroll_reports_are_grouped(self):
        groups = {group: [i[1] for i in items] for group, items in MENU}
        self.assertIn("Monthly Attendance Sheet", groups["HR Reports"])
        self.assertIn("Salary Register", groups["Payroll Reports"])
        self.assertIn("Bank Remittance", groups["Payroll Reports"])

    def test_obsolete_page_is_not_listed(self):
        self.assertNotIn("reckon-hrms-payout", [i[1] for _g, items in MENU for i in items if i[0] == "Page"])

    def test_every_report_has_an_icon(self):
        for _group, items in MENU:
            for item in items:
                if item[0] in ("Report", "DocType"):
                    self.assertIn(item[1], ICONS, item[1])


if __name__ == "__main__":
    unittest.main()
