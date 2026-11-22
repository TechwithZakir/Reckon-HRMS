"""The Company and employee setup screen shows only the signed-in company's records and headcounts (file-text checks, no Frappe)."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "reckon_hrms"
API = (ROOT / "api" / "setup.py").read_text(encoding="utf-8")
JS = (ROOT / "public" / "js" / "reckon_setup_stages.js").read_text(encoding="utf-8")


class ScopeTests(unittest.TestCase):
    def test_headcounts_count_only_the_companys_employees(self):
        sql = re.search(r"SELECT `\{field\}`.*?GROUP BY", API, re.DOTALL).group(0)
        self.assertIn("`company` = %(company)s", sql)

    def test_lists_use_the_servers_company_and_ignore_the_one_the_page_sends(self):
        body = API[API.index("def list_items"): API.index("def create_item")]
        self.assertIn("_mine()", body)
        self.assertIn("_own_filters(doctype, mine)", body)
        self.assertNotIn('filters = {"company": company}', body)
        self.assertNotIn("args.company", JS[JS.index("function loadChips"): JS.index("function addItem")])

    def test_the_checklist_counts_this_companys_records_only(self):
        body = API[API.index("def get_state"):]
        for needle in ("_own_filters(dt, mine)", '{"company": mine}'):
            self.assertIn(needle, body)
        self.assertNotIn("frappe.db.count(dt)", body)
        self.assertNotIn('frappe.db.count("Employee")', body)
        self.assertNotIn('frappe.db.count("Shift Type")', body)

    def test_a_delete_of_another_companys_record_is_refused(self):
        body = API[API.index("def delete_item"): API.index("def get_state")]
        self.assertIn("does not belong to your company", body)

    def test_the_screen_shows_the_plain_label_not_the_company_suffix_and_hides_suggestions_already_added(self):
        self.assertIn("row.label || row.name", JS)
        self.assertIn("$(this).toggle(!have.has(name))", JS)

    def test_the_industry_is_a_step_of_the_checklist_and_there_is_one_place_to_choose_it(self):
        self.assertIn('"key": "industry"', API)
        self.assertNotIn("choose_segment", JS)
        self.assertIn("Review or change it in Guided setup", JS)


if __name__ == "__main__":
    unittest.main()


SALARY = (ROOT / "api" / "salary.py").read_text(encoding="utf-8")


class SalaryScopeTests(unittest.TestCase):
    """The Payroll Studio salary screens never act on a company the page sends."""

    def test_structures_and_the_assignment_summary_use_the_servers_company(self):
        self.assertIn('filters = {"company": _mine()}', SALARY)
        body = SALARY[SALARY.index("def assignment_summary"): SALARY.index("def bulk_assign")]
        self.assertIn("company = _mine()", body)
        self.assertNotIn("if company:", body)

    def test_bulk_assign_only_touches_the_own_company_and_only_its_own_structure(self):
        body = SALARY[SALARY.index("def bulk_assign"): SALARY.index("def run_bulk_assign")]
        self.assertIn("company = _mine()", body)
        self.assertIn('"company": company}', body)
        self.assertIn("company=company", body)

    def test_the_component_total_is_what_the_person_may_see(self):
        self.assertNotIn('frappe.db.count("Salary Component")', SALARY)


class SuggestionTests(unittest.TestCase):
    def test_department_and_job_title_suggestions_come_from_the_industry_and_skip_what_exists(self):
        body = API[API.index("def _suggestions"): API.index("def create_item") if "def create_item" in API[API.index("def _suggestions"):] else len(API)]
        self.assertIn("reckon_industry", body)
        self.assertIn("similar_department(n, have)", body)

    def test_the_screen_uses_the_servers_suggestions_when_it_sends_them(self):
        self.assertIn("Array.isArray(r.message.suggest)", JS)
