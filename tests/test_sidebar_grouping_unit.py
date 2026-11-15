"""The left menu: one-item groups are plain links, bigger groups keep a heading over their related items."""

import sys
import types
import unittest

stub = types.ModuleType("frappe")
stub.db = types.SimpleNamespace(exists=lambda *a, **k: True)
sys.modules.setdefault("frappe", stub)

from reckon_hrms.patches import desk_menu_arrangement as arrange  # noqa: E402


class SidebarGroupingTests(unittest.TestCase):
    def setUp(self):
        self.items = arrange._sidebar_items()

    def test_single_item_groups_have_no_heading(self):
        headings = [i["label"] for i in self.items if i["type"] == "Section Break"]
        for single in ("Home", "HR Studio", "Payroll Studio", "Dashboard"):
            self.assertNotIn(single, headings)
        labels = [i["label"] for i in self.items if i["type"] == "Link"]
        self.assertEqual(labels[:4], ["Home", "HR Studio", "Payroll Studio", "Dashboard"])

    def test_related_items_stay_under_their_heading_in_order(self):
        order = [(i["type"], i["label"]) for i in self.items]
        start = order.index(("Section Break", "People"))
        self.assertEqual([label for _t, label in order[start + 1:start + 4]], ["Employee", "Department", "Designation"])
        self.assertIn(("Section Break", "Leave & Expense"), order)
        self.assertIn(("Section Break", "Payroll"), order)

    def test_group_items_are_children_of_their_heading_and_single_links_stand_alone(self):
        by = {i["label"]: i for i in self.items}
        self.assertEqual((by["People"]["child"], by["People"]["indent"], by["People"]["icon"]), (0, 0, "users"))
        self.assertEqual((by["Employee"]["child"], by["Employee"]["indent"]), (1, 0))  # the Accounts menu shape
        self.assertEqual((by["Home"]["child"], by["Home"]["indent"]), (0, 0))


if __name__ == "__main__":
    unittest.main()
