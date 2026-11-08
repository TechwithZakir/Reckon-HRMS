import unittest

from reckon_hrms import paging
from reckon_hrms.api import shortcuts


class PagingTests(unittest.TestCase):
    def test_clamps_length_and_start(self):
        self.assertEqual(paging.page_bounds(-5, 500), (0, 100))
        self.assertEqual(paging.page_bounds(10, 0), (10, 25))
        self.assertEqual(paging.page_bounds("abc", None), (0, 25))
        self.assertEqual(paging.page_bounds(0, 1), (0, 1))


class RouteTests(unittest.TestCase):
    def test_list_new_and_form_routes(self):
        self.assertEqual(shortcuts.route("Branch"), "/app/branch")
        self.assertEqual(shortcuts.route("Branch", "new"), "/app/branch/new")
        self.assertEqual(shortcuts.route("Employment Type", "list"), "/app/employment-type")
        self.assertEqual(shortcuts.route("Payroll Entry", "form", "HR-PRL-1"), "/app/payroll-entry/HR-PRL-1")

    def test_unknown_action_and_missing_name_rejected(self):
        with self.assertRaises(ValueError):
            shortcuts.route("Branch", "delete")
        with self.assertRaises(ValueError):
            shortcuts.route("Branch", "form")

    def test_unlisted_doctype_gets_default_slug(self):
        self.assertEqual(shortcuts.route("Shift Assignment"), "/app/shift-assignment")


if __name__ == "__main__":
    unittest.main()
