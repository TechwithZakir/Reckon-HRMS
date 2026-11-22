"""Every HR and payroll endpoint stays inside the signed-in company: the guard module, and no unguarded id lookups (no Frappe site)."""

import re
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

API = Path(__file__).resolve().parents[1] / "reckon_hrms" / "api"


class Perm(Exception):
    pass


def load_scope(test, company="Acme", records=None, employees=None):
    frappe = types.ModuleType("frappe")
    frappe._ = lambda t: t
    frappe.PermissionError = Perm

    def throw(msg, exc=Exception):
        raise exc(msg)

    frappe.throw = throw
    records = records or {}

    class Doc(dict):
        def get(self, key, default=None):
            return dict.get(self, key, default)

    frappe.get_doc = lambda doctype, name: Doc(records[(doctype, name)])
    frappe.db = types.SimpleNamespace(get_value=lambda dt, name, field: (employees or {}).get(name))
    frappe.get_meta = lambda dt: types.SimpleNamespace(has_field=lambda f: dt != "Leave Policy Plain")
    home = types.ModuleType("reckon_hrms.api.home")
    home._company = lambda: company
    pkg = types.ModuleType("reckon_hrms")
    pkg.__path__ = []
    api = types.ModuleType("reckon_hrms.api")
    api.__path__ = []
    mods = {"frappe": frappe, "reckon_hrms": pkg, "reckon_hrms.api": api, "reckon_hrms.api.home": home}
    patcher = patch.dict(sys.modules, mods)  # kept for the whole test: scope.py imports the platform lazily
    patcher.start()
    test.addCleanup(patcher.stop)
    import importlib.util

    spec = importlib.util.spec_from_file_location("reckon_hrms.api.scope_under_test", API / "scope.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, frappe


class GuardTests(unittest.TestCase):
    def test_a_record_of_another_company_is_refused_and_an_own_one_is_returned(self):
        mod, _f = load_scope(self, "Acme", {("Payroll Entry", "PE-1"): {"company": "Acme"}, ("Payroll Entry", "PE-2"): {"company": "Rahman Textiles Ltd."}})
        self.assertEqual(mod.own_doc("Payroll Entry", "PE-1")["company"], "Acme")
        with self.assertRaises(Perm):
            mod.own_doc("Payroll Entry", "PE-2")

    def test_a_record_without_a_company_field_is_not_blocked_by_the_company_check(self):
        mod, _f = load_scope(self, "Acme", {("Thing", "T-1"): {"title": "x"}})
        self.assertEqual(mod.own_doc("Thing", "T-1")["title"], "x")

    def test_an_employee_of_another_company_is_refused(self):
        mod, _f = load_scope(self, "Acme", employees={"E-1": "Acme", "E-2": "Rahman Textiles Ltd.", "E-3": None})
        self.assertEqual(mod.own_employee("E-1"), "E-1")
        for other in ("E-2", "E-3", "E-404"):
            with self.assertRaises(Perm):
                mod.own_employee(other)

    def test_shared_catalog_filters_are_this_companys_and_the_standard_ones(self):
        mod, _f = load_scope(self, "Acme")
        self.assertEqual(mod.shared_or_own("Salary Component"), {"company": ["in", ["Acme", "", None]]})
        self.assertEqual(mod.shared_or_own("Leave Policy Plain"), {})


class NoUnguardedLookupTests(unittest.TestCase):
    """The endpoints that take an id from the page must load it through the guard."""

    def read(self, name):
        return (API / name).read_text(encoding="utf-8")

    def test_no_endpoint_loads_a_payroll_run_by_the_pages_id_without_the_guard(self):
        for name in ("payroll_run.py", "adjustments.py", "deductions.py", "slip_report.py", "ops.py"):
            text = self.read(name)
            self.assertNotIn('frappe.get_doc("Payroll Entry", name)', text, name)
            self.assertNotIn('frappe.get_doc("Payroll Entry", payroll_entry)', text, name)

    def test_the_guarded_endpoints_use_it(self):
        self.assertGreaterEqual(self.read("payroll_run.py").count('own_doc("Payroll Entry", name)'), 10)
        self.assertIn('own_doc("Payroll Entry", name)', self.read("slip_report.py"))
        self.assertIn('own_doc("Payroll Entry", name)', self.read("deductions.py"))
        self.assertIn("own_employee(employee)", self.read("adjustments.py"))
        self.assertIn('own_doc("Additional Salary", request)', self.read("adjustments.py"))
        self.assertIn('own_doc("Payroll Entry", payroll_entry)', self.read("ops.py"))
        self.assertIn("own_employee(employee)", self.read("ops.py"))
        self.assertIn('own_doc(doctype, name)', self.read("approvals.py"))

    def test_the_biometric_import_matches_device_ids_inside_the_own_company(self):
        self.assertIn('"attendance_device_id": p["employee_code"], "company": mine()', self.read("ops.py"))

    def test_catalog_lists_are_limited_to_own_and_standard_records(self):
        for name, marker in (("payout.py", 'shared_or_own("Salary Component")'), ("people.py", "shared_or_own(doctype)"), ("ops.py", 'shared_or_own("Leave Type")')):
            self.assertIn(marker, self.read(name), name)

    def test_no_endpoint_trusts_a_company_sent_by_the_page(self):
        salary = self.read("salary.py")
        self.assertIn('filters = {"company": _mine()}', salary)
        self.assertEqual(len(re.findall(r'filters = \{"company": company\} if company else \{\}', salary)), 0)


if __name__ == "__main__":
    unittest.main()
