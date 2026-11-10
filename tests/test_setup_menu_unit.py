"""Unit tests: Setup is the first left-nav group and its page exists (no Frappe)."""

import unittest
from pathlib import Path

from reckon_hrms.menu import MENU

APP = Path(__file__).resolve().parents[1] / "reckon_hrms"


class SetupMenuTests(unittest.TestCase):
    def test_hr_studio_is_the_first_group(self):
        self.assertEqual(MENU[0][0], "HR Studio")

    def test_payroll_studio_links_the_payroll_page(self):
        pages = [item for item in MENU[1][1] if item[0] == "Page"]
        self.assertEqual(pages, [("Page", "reckon-hrms-setup", "Payroll Studio")])

    def test_setup_page_folder_exists(self):
        folder = APP / "reckon_hrms" / "page" / "reckon_hrms_setup"
        self.assertTrue((folder / "reckon_hrms_setup.js").exists())
        self.assertTrue((folder / "reckon_hrms_setup.json").exists())

    def test_old_stage_pages_redirect_into_setup(self):
        for name, target in (("reckon_hrms_salary", "reckon-hrms-setup"), ("reckon_hrms_run", "reckon-hrms-setup"),
                             ("reckon_hrms_company", "reckon-hrms-hr-studio")):
            text = (APP / "reckon_hrms" / "page" / name / f"{name}.js").read_text(encoding="utf-8")
            self.assertIn(f'frappe.set_route("{target}")', text)

    def test_stage_file_defines_all_three_stages(self):
        text = (APP / "public" / "js" / "reckon_setup_stages.js").read_text(encoding="utf-8")
        for stage in ("company", "salary", "run"):
            self.assertIn(f"window.ReckonSetupStages.{stage} = function", text)


if __name__ == "__main__":
    unittest.main()
