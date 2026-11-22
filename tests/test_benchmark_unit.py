"""Unit tests for the 2026 payroll benchmark data and the salary suggestion rules (no Frappe)."""

import json
import unittest
from pathlib import Path

from reckon_hrms import salary_suggest

DATA_PATH = Path(__file__).resolve().parents[1] / "reckon_hrms" / "benchmarks" / "payroll_benchmark_2026.json"


class BenchmarkDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DATA_PATH, encoding="utf-8") as fh:
            cls.data = json.load(fh)

    def test_role_count_matches_workbook(self):
        total = sum(len(seg["roles"]) for seg in self.data["segments"].values())
        self.assertEqual(total, 28)
        self.assertEqual(self.data["role_count"], 28)

    def test_every_midpoint_is_the_average_of_min_and_max(self):
        for key, seg in self.data["segments"].items():
            for role in seg["roles"]:
                with self.subTest(segment=key, role=role["role"]):
                    self.assertLessEqual(role["min"], role["midpoint"], role["role"])
                    self.assertLessEqual(role["midpoint"], role["max"], role["role"])
                    self.assertLessEqual(abs((role["min"] + role["max"]) / 2 - role["midpoint"]), 1)

    def test_confidence_is_only_low_or_medium(self):
        for seg in self.data["segments"].values():
            for role in seg["roles"]:
                self.assertIn(role["confidence"], {"Low", "Medium"})

    def test_every_segment_has_components_departments_and_leave_types(self):
        for key, seg in self.data["segments"].items():
            with self.subTest(segment=key):
                self.assertTrue(seg["roles"])
                self.assertTrue(seg["components"])
                self.assertTrue(seg["departments"])
                self.assertIn("Casual Leave", seg["leave_types"])

    def test_leave_types_carry_no_entitlement_days(self):
        # The guide says leave rules are company-configured; the data must not hard-code days.
        self.assertNotIn("max_leaves_allowed", json.dumps(self.data))


class SuggestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DATA_PATH, encoding="utf-8") as fh:
            cls.data = json.load(fh)

    def test_exact_role_match_returns_band_and_midpoint(self):
        result = salary_suggest.suggest("it_software", "Senior Software Engineer", data=self.data)
        self.assertEqual(result["status"], "matched")
        self.assertEqual((result["min"], result["max"], result["midpoint"]), (100000, 180000, 140000))
        self.assertIn("not a guaranteed salary", result["caveat"])

    def test_partial_name_matches_within_segment(self):
        result = salary_suggest.suggest("it_software", "devops", data=self.data)
        self.assertEqual(result["role"], "DevOps / Cloud Engineer")

    def test_close_spelling_is_matched(self):
        result = salary_suggest.suggest("corporate_finance", "Accountant", data=self.data)
        self.assertEqual(result["role"], "Accountant / Finance Executive")

    def test_unknown_role_is_a_research_gap_not_an_estimate(self):
        result = salary_suggest.suggest("it_software", "Chief Wizard", data=self.data)
        self.assertEqual(result["status"], "no_match")
        self.assertNotIn("midpoint", result)

    def test_unknown_segment_is_reported(self):
        self.assertEqual(salary_suggest.suggest("space_mining", "Engineer", data=self.data)["status"],
                         "unknown_segment")

    def test_position_in_band(self):
        below = salary_suggest.position_in_band(10000, 20000, 30000)
        within = salary_suggest.position_in_band(25000, 20000, 30000)
        above = salary_suggest.position_in_band(40000, 20000, 30000)
        self.assertEqual(below["position"], "below")
        self.assertEqual((within["position"], within["percent_into_band"]), ("within", 50.0))
        self.assertEqual(above["position"], "above")

    def test_current_gross_is_reported_against_band(self):
        result = salary_suggest.suggest("it_software", "Junior Software Developer", current_gross=47500,
                                        data=self.data)
        self.assertEqual(result["position"], "within")
        self.assertEqual(result["percent_into_band"], 50.0)


if __name__ == "__main__":
    unittest.main()


class IndustryPreviewTests(unittest.TestCase):
    """The guided setup shows what an industry would load before anything is added."""

    @classmethod
    def setUpClass(cls):
        import sys
        import types

        sys.modules.setdefault("frappe", types.ModuleType("frappe"))  # the preview rules are pure; the module only imports frappe
        from reckon_hrms import industry_seed

        cls.seed = industry_seed
        with open(DATA_PATH, encoding="utf-8") as fh:
            cls.data = json.load(fh)

    def empty(self, **extra):
        base = {"designations": set(), "departments": set(), "leave_types": set(), "components": set(), "code_taken": set(), "overtime": False}
        base.update(extra)
        return base

    def test_a_blank_company_would_get_everything_the_industry_lists(self):
        seg = self.data["segments"]["manufacturing_rmg_textile"]
        preview = self.seed.build_preview(seg, self.empty())
        self.assertEqual(preview["will_add"]["designations"], len(seg["roles"]))
        self.assertEqual(preview["will_add"]["departments"], len(seg["departments"]))
        self.assertEqual(preview["will_add"]["leave_types"], len(seg["leave_types"]))
        self.assertEqual(preview["will_add"]["overtime"], 1)
        self.assertTrue(all(i["status"] == "new" for g in preview["groups"] for i in g["items"]))
        self.assertTrue(any("nothing is paid" in line.lower() for line in preview["not_loaded"]))

    def test_what_already_exists_is_marked_and_not_counted(self):
        seg = self.data["segments"]["pharmaceuticals"]
        have = self.empty(departments={"Production"}, components={"Basic Salary"}, overtime=True, code_taken={"Sales Commission"})
        preview = self.seed.build_preview(seg, have)
        by = {g["key"]: {i["name"]: i["status"] for i in g["items"]} for g in preview["groups"]}
        self.assertEqual(by["departments"]["Production"], "exists")
        self.assertEqual(by["components"]["Basic Salary"], "exists")
        self.assertEqual(by["components"]["Sales Commission"], "skipped")
        self.assertEqual(by["overtime"]["Standard Overtime"], "exists")
        self.assertEqual(preview["will_add"]["overtime"], 0)

    def test_an_industry_without_overtime_has_no_overtime_rule(self):
        preview = self.seed.build_preview(self.data["segments"]["sales_marketing"], self.empty())
        self.assertNotIn("overtime", [g["key"] for g in preview["groups"]])

    def test_preview_never_carries_pay_amounts(self):
        preview = self.seed.build_preview(self.data["segments"]["it_software"], self.empty())
        self.assertNotIn("min", json.dumps(preview))
