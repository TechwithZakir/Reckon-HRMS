import unittest
from decimal import Decimal

from reckon_hrms import bd_payroll as bd


class TaxTests(unittest.TestCase):
    def test_tax_free_band(self):
        self.assertEqual(bd.annual_tax(350000), Decimal("0"))

    def test_first_taxable_band(self):
        self.assertEqual(bd.annual_tax(400000), Decimal("2500.00"))

    def test_mid_band(self):
        # 5% of 100,000 + 10% of 150,000 = 5,000 + 15,000 = 20,000 on 600,000
        self.assertEqual(bd.annual_tax(600000), Decimal("20000.00"))

    def test_top_band(self):
        # 5,000 + 30,000 + 37,500 for 1,000,000
        self.assertEqual(bd.annual_tax(1000000), Decimal("72500.00"))

    def test_monthly_tds_with_pf_exemption(self):
        self.assertEqual(bd.monthly_tds(50000), Decimal("1666.67"))
        # PF of 2,500 a month lowers taxable income to 47,500 a month (570,000 a year)
        # 570,000 a year: 5% of 100,000 + 10% of 120,000 = 17,000, so 1,416.67 a month
        self.assertEqual(bd.monthly_tds(50000, 2500), Decimal("1416.67"))


class FestivalBonusTests(unittest.TestCase):
    def test_full_year_is_one_basic_split_across_two_festivals(self):
        self.assertEqual(bd.festival_bonus(20000, 12), Decimal("10000.00"))

    def test_pro_rata_under_a_year(self):
        self.assertEqual(bd.festival_bonus(20000, 6), Decimal("5000.00"))

    def test_no_service_no_bonus(self):
        self.assertEqual(bd.festival_bonus(20000, 0), Decimal("0"))


class LabelAndSheetTests(unittest.TestCase):
    def test_bangla_digits(self):
        self.assertEqual(bd.to_bangla_digits(1234.5), "১,২৩৪.৫০")

    def test_bilingual_fallback(self):
        self.assertEqual(bd.bilingual("Unknown Thing"), ("Unknown Thing", "Unknown Thing"))
        self.assertEqual(bd.bilingual("Basic Salary")[1], "মূল বেতন")

    def test_bank_sheet(self):
        rows = bd.bank_sheet_rows([{"employee": "HR-EMP-1", "employee_name": "Rahim", "bank_name": "Sonali",
                                    "bank_ac_no": "0011", "net_pay": 25000.555}])
        self.assertEqual(rows[0], ["Employee", "Name", "Bank", "Account", "Net Pay"])
        self.assertEqual(rows[1], ["HR-EMP-1", "Rahim", "Sonali", "0011", "25000.56"])


if __name__ == "__main__":
    unittest.main()
