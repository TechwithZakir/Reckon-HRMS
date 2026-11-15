"""Everything the left menu offers must be allowed by the module registration, or a tenant meets
"X is not available in your workspace" / "Page X is not available"."""

import unittest
from pathlib import Path

from reckon_hrms.constants import DESK_DOCTYPES, DESK_PAGES, TENANT_OWNED_DOCTYPES
from reckon_hrms.menu import MENU
from reckon_hrms.saas_module import get_module_definition

PAGE_DIR = Path(__file__).resolve().parents[1] / "reckon_hrms" / "reckon_hrms" / "page"


class DeskAllowlistTests(unittest.TestCase):
    def test_every_menu_doctype_is_allowed(self):
        wanted = {item[1] for _g, items in MENU for item in items if item[0] == "DocType"}
        self.assertEqual(sorted(wanted - set(DESK_DOCTYPES)), [])

    def test_every_menu_page_and_every_page_folder_is_allowed(self):
        wanted = {item[1] for _g, items in MENU for item in items if item[0] == "Page"}
        folders = {p.name.replace("_", "-") for p in PAGE_DIR.iterdir() if p.is_dir() and not p.name.startswith("__")}
        self.assertEqual(sorted((wanted | folders) - set(DESK_PAGES)), [])

    def test_the_registration_publishes_pages_and_reports(self):
        definition = get_module_definition()
        self.assertIn("reckon-hrms-setup", definition["desk_pages"])
        self.assertIn("Salary Register", definition["desk_reports"])
        self.assertIn("Expense Claim Type", definition["desk_doctypes"])

    def test_expense_claim_has_a_company_so_it_is_tenant_owned(self):
        self.assertIn("Expense Claim", TENANT_OWNED_DOCTYPES)


if __name__ == "__main__":
    unittest.main()
