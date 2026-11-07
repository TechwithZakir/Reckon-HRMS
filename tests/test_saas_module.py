"""Framework-free contract tests for the Reckon HRMS SaaS registration.

Run: python -m unittest discover -s tests
"""

import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reckon_hrms.constants import tenant_role  # noqa: E402
from reckon_hrms.constants import MODULE_FEATURES, ROLES, TENANT_OWNED_DOCTYPES  # noqa: E402
from reckon_hrms.saas_module import get_module_definition  # noqa: E402

REQUIRED_KEYS = {
    "key",
    "label",
    "workspace",
    "home_route",
    "admin_role",
    "roles",
    "seed_handler",
    "subscription_features",
}


class SaaSModuleContractTests(unittest.TestCase):
    def setUp(self):
        self.definition = get_module_definition()

    def test_has_every_key_the_platform_reads(self):
        self.assertTrue(REQUIRED_KEYS.issubset(self.definition))

    def test_admin_role_is_one_of_the_module_roles(self):
        self.assertIn(self.definition["admin_role"], self.definition["roles"])

    def test_roles_match_constants(self):
        self.assertEqual(self.definition["roles"], list(ROLES))

    def test_features_are_the_four_version_one_modules(self):
        self.assertEqual(
            self.definition["subscription_features"],
            ["employees", "attendance_shifts", "leave", "payroll"],
        )
        self.assertEqual(set(self.definition["subscription_features"]), set(MODULE_FEATURES))

    def test_seed_handler_points_at_a_defined_function(self):
        module_path, function_name = self.definition["seed_handler"].rsplit(".", 1)
        self.assertEqual(module_path, "reckon_hrms.seed")
        seed_source = (ROOT / "reckon_hrms" / "seed.py").read_text(encoding="utf-8")
        self.assertRegex(seed_source, rf"def {function_name}\(company: str, seed_version: str\)")


class TenantOwnedDoctypeTests(unittest.TestCase):
    def test_list_is_non_empty_and_unique(self):
        self.assertTrue(TENANT_OWNED_DOCTYPES)
        self.assertEqual(len(TENANT_OWNED_DOCTYPES), len(set(TENANT_OWNED_DOCTYPES)))

    def test_employee_and_payroll_core_are_covered(self):
        for doctype in ("Employee", "Attendance", "Salary Slip", "Payroll Entry"):
            self.assertIn(doctype, TENANT_OWNED_DOCTYPES)

    def test_every_entry_is_a_plain_doctype_name(self):
        for doctype in TENANT_OWNED_DOCTYPES:
            self.assertRegex(doctype, r"^[A-Za-z][A-Za-z &]+$")


class TenantRoleTests(unittest.TestCase):
    def test_role_names_are_per_company(self):
        self.assertEqual(tenant_role("Admin", "Acme Ltd"), "Reckon HRMS Admin - Acme Ltd")
        self.assertNotEqual(tenant_role("User", "A"), tenant_role("User", "B"))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            tenant_role("Manager", "Acme")


if __name__ == "__main__":
    unittest.main()
