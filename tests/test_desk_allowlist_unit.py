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


class TenantScopingTests(unittest.TestCase):
    """A doctype a tenant can open must be scoped to the tenant: no row of another company may show."""

    def test_every_reachable_doctype_has_a_scoping_rule(self):
        from reckon_hrms import hooks
        from reckon_hrms.constants import EMPLOYEE_CHECKIN, HOLIDAY_ASSIGNMENT, READ_ONLY_SETTINGS, SHARED_CATALOG_DOCTYPES

        scoped = set(TENANT_OWNED_DOCTYPES) | set(SHARED_CATALOG_DOCTYPES) | set(READ_ONLY_SETTINGS) | {EMPLOYEE_CHECKIN, HOLIDAY_ASSIGNMENT}
        self.assertEqual(sorted(set(DESK_DOCTYPES) - scoped), [])
        for doctype in set(DESK_DOCTYPES):
            if doctype not in READ_ONLY_SETTINGS:  # single records have no rows to filter
                self.assertIn(doctype, hooks.permission_query_conditions, doctype)
            self.assertIn(doctype, hooks.has_permission, doctype)

    def test_company_less_masters_get_a_company_field_and_stamping(self):
        from reckon_hrms import hooks
        from reckon_hrms.constants import SHARED_CATALOG_DOCTYPES

        for doctype in SHARED_CATALOG_DOCTYPES:
            self.assertEqual(hooks.permission_query_conditions[doctype], "reckon_saas_platform.tenant_security.get_tenant_shared_query")
            self.assertIn("bind_catalog_company", hooks.doc_events[doctype]["before_validate"])
        patch = (Path(__file__).resolve().parents[1] / "reckon_hrms" / "patches.txt").read_text(encoding="utf-8")
        self.assertIn("reckon_hrms.patches.company_on_shared_masters", patch)


class ComponentAccountsTests(unittest.TestCase):
    def test_a_slip_validates_with_both_the_company_stamp_and_the_account_fill(self):
        from reckon_hrms import hooks

        self.assertIn("reckon_hrms.tenancy_hooks.bind_company", hooks.doc_events["Salary Slip"]["before_validate"])
        for event in ("validate", "before_submit"):
            self.assertIn("reckon_hrms.component_accounts.ensure_component_accounts", hooks.doc_events["Salary Slip"][event])
