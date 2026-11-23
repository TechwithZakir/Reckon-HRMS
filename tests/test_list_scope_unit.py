"""Every HR and payroll list is limited to a company: a tenant's own, a vendor user's selected Default Company (file and stub checks, no site)."""

import re
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / "reckon_hrms"
HOOKS = (ROOT / "hooks.py").read_text(encoding="utf-8")
CONSTANTS = (ROOT / "constants.py").read_text(encoding="utf-8")
TEN = (ROOT / "tenancy_hooks.py").read_text(encoding="utf-8")


def extra():
    block = CONSTANTS[CONSTANTS.index("EXTRA_SCOPED_DOCTYPES = ("):]
    block = block[: block.index(")\n")]
    return re.findall(r'"([^"]+)"', block)


class HookTests(unittest.TestCase):
    def test_the_unscoped_hr_and_payroll_doctypes_are_now_scoped(self):
        names = extra()
        self.assertGreaterEqual(len(names), 39)
        for name in ("Job Opening", "Employee Onboarding", "Job Offer", "Overtime Slip", "Payroll Period", "Appraisal", "Gratuity"):
            self.assertIn(name, names)
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("_SCOPED = TENANT_OWNED_DOCTYPES + EXTRA_SCOPED_DOCTYPES", HOOKS)
        self.assertEqual(HOOKS.count("for doctype in _SCOPED"), 3)  # query, permission and company stamping

    def test_the_scoped_extras_are_not_added_to_the_tenants_desk_reach(self):
        desk = CONSTANTS[CONSTANTS.index("DESK_DOCTYPES = "): CONSTANTS.index("SHARED_CATALOG_DOCTYPES = (")]
        self.assertNotIn("EXTRA_SCOPED_DOCTYPES", desk)

    def test_lists_use_the_company_aware_queries_and_applicants_go_through_their_opening(self):
        self.assertIn('"reckon_hrms.tenancy_hooks.owned_query"', HOOKS)
        self.assertIn('"reckon_hrms.tenancy_hooks.shared_query"', HOOKS)
        self.assertIn('permission_query_conditions["Job Applicant"] = "reckon_hrms.tenancy_hooks.job_applicant_query"', HOOKS)
        self.assertNotIn('"reckon_saas_platform.tenant_security.get_tenant_owned_query"', HOOKS)


def load(user_bypass=True, default_company="Acme", base_owned="", base_shared="", tenant_company=None):
    frappe = types.ModuleType("frappe")
    frappe.session = types.SimpleNamespace(user="vendor@x.test")
    frappe.db = types.SimpleNamespace(escape=lambda v: "'" + str(v).replace("'", "''") + "'")
    frappe.defaults = types.SimpleNamespace(get_user_default=lambda key, user=None: default_company)
    sec = types.ModuleType("reckon_saas_platform.tenant_security")
    sec.user_can_bypass_tenant = lambda user=None: user_bypass
    sec.get_tenant_owned_query = lambda user=None, doctype=None: base_owned
    sec.get_tenant_shared_query = lambda user=None, doctype=None: base_shared
    for name in ("bind_doc_to_tenant", "validate_tenant_company_immutable", "validate_tenant_owned_doc"):
        setattr(sec, name, lambda *a, **k: None)
    sec.tenant_company_or_none = lambda user=None: tenant_company
    pkg = types.ModuleType("reckon_saas_platform")
    pkg.__path__ = []
    mods = {"frappe": frappe, "reckon_saas_platform": pkg, "reckon_saas_platform.tenant_security": sec}
    return mods


class QueryTests(unittest.TestCase):
    def mod(self, **kw):
        mods = load(**kw)
        patcher = patch.dict(sys.modules, mods)
        patcher.start()
        self.addCleanup(patcher.stop)
        import importlib.util

        spec = importlib.util.spec_from_file_location("tenancy_under_test", ROOT / "tenancy_hooks.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_vendor_staff_see_only_the_selected_default_company(self):
        m = self.mod()
        self.assertEqual(m.owned_query("vendor@x.test", "Employee"), "`tabEmployee`.`company` = 'Acme'")
        self.assertIn("`tabBranch`.`company` = 'Acme'", m.shared_query("vendor@x.test", "Branch"))
        self.assertIn("ifnull(`tabBranch`.`company`, '') = ''", m.shared_query("vendor@x.test", "Branch"))

    def test_without_a_selected_company_vendor_staff_still_see_everything(self):
        m = self.mod(default_company=None)
        self.assertEqual(m.owned_query("vendor@x.test", "Employee"), "")
        self.assertEqual(m.shared_query("vendor@x.test", "Branch"), "")

    def test_a_tenants_own_rule_is_kept_and_a_tenant_never_gets_the_default_company_path(self):
        m = self.mod(user_bypass=False, base_owned="`tabEmployee`.`company` = 'Rahman'", base_shared="X")
        self.assertEqual(m.owned_query("t@x.test", "Employee"), "`tabEmployee`.`company` = 'Rahman'")
        self.assertEqual(m.shared_query("t@x.test", "Branch"), "X")
        self.assertIsNone(m._selected_company("t@x.test"))

    def test_the_company_name_is_escaped(self):
        m = self.mod(default_company="O'Neil Ltd")
        self.assertEqual(m.owned_query("v", "Employee"), "`tabEmployee`.`company` = 'O''Neil Ltd'")


if __name__ == "__main__":
    unittest.main()
