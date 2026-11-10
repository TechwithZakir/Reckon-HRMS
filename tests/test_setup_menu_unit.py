"""Unit tests: Setup is the first left-nav group and its page exists (no Frappe)."""

import unittest
from pathlib import Path

from reckon_hrms.menu import MENU

APP = Path(__file__).resolve().parents[1] / "reckon_hrms"


class SetupMenuTests(unittest.TestCase):
    def test_setup_is_the_first_group(self):
        self.assertEqual(MENU[0][0], "Setup")

    def test_setup_group_links_the_single_setup_page(self):
        pages = [item for item in MENU[0][1] if item[0] == "Page"]
        self.assertEqual(pages, [("Page", "reckon-hrms-setup", "Setup")])

    def test_setup_page_folder_exists(self):
        folder = APP / "reckon_hrms" / "page" / "reckon_hrms_setup"
        self.assertTrue((folder / "reckon_hrms_setup.js").exists())
        self.assertTrue((folder / "reckon_hrms_setup.json").exists())

    def test_old_stage_pages_redirect_into_setup(self):
        for name in ("reckon_hrms_company", "reckon_hrms_salary", "reckon_hrms_run"):
            text = (APP / "reckon_hrms" / "page" / name / f"{name}.js").read_text(encoding="utf-8")
            self.assertIn('frappe.set_route("reckon-hrms-setup")', text)

    def test_stage_file_defines_all_three_stages(self):
        text = (APP / "public" / "js" / "reckon_setup_stages.js").read_text(encoding="utf-8")
        for stage in ("company", "salary", "run"):
            self.assertIn(f"window.ReckonSetupStages.{stage} = function", text)


if __name__ == "__main__":
    unittest.main()
