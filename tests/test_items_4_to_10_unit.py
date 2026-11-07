import unittest
from decimal import Decimal

from reckon_hrms import anomaly, bio, messaging, statutory


class StatutoryTests(unittest.TestCase):
    def test_wppf_applies_to_ten_or_more_workers(self):
        self.assertEqual(statutory.wppf_contribution(1000000, 20), Decimal("50000.00"))
        self.assertEqual(statutory.wppf_contribution(1000000, 5), Decimal("0.00"))
        self.assertEqual(statutory.wppf_contribution(-5000, 20), Decimal("0.00"))

    def test_gratuity_first_five_years_then_longer_rate(self):
        # daily 1000 (30,000 / 30); 3 years * 14 days = 42,000
        self.assertEqual(statutory.gratuity(30000, 3), Decimal("42000.00"))
        # 5 * 14 + 2 * 30 = 130 days = 130,000
        self.assertEqual(statutory.gratuity(30000, 7), Decimal("130000.00"))
        self.assertEqual(statutory.gratuity(30000, 0.9), Decimal("0.00"))

    def test_provident_fund_split(self):
        self.assertEqual(statutory.provident_fund(30000), {"employee": Decimal("1500.00"),
                                                           "employer": Decimal("1500.00")})


class BiometricTests(unittest.TestCase):
    def test_parses_and_sorts_punches(self):
        text = ("employee,time,direction\n"
                "E2,07-11-2026 09:30,0\n"
                "E1,2026-11-07 17:02:00,OUT\n"
                "E1,2026-11-07 09:01:00,IN\n"
                "E1,not a time,IN\n")
        punches, errors = bio.parse_punches(text)
        self.assertEqual([p["employee_code"] for p in punches], ["E1", "E1", "E2"])
        self.assertEqual(punches[2]["log_type"], "IN")
        self.assertEqual(len(errors), 1)

    def test_infers_direction_when_missing(self):
        text = "employee,time\nE1,2026-11-07 09:00\nE1,2026-11-07 17:00\nE1,2026-11-08 09:00\n"
        punches, _ = bio.parse_punches(text)
        directions = [p["log_type"] for p in bio.infer_directions(punches)]
        self.assertEqual(directions, ["IN", "OUT", "IN"])

    def test_missing_columns_rejected(self):
        with self.assertRaises(ValueError):
            bio.parse_punches("foo,bar\n1,2\n")


class MessagingTests(unittest.TestCase):
    def test_unconfigured_adapter_skips(self):
        msgs = [messaging.Message("017", "hi"), messaging.Message("018", "hi", "whatsapp")]
        res = messaging.dispatch(msgs, messaging.WebhookAdapter(None, None))
        self.assertEqual((res.sent, res.skipped, res.failed), (0, 2, []))

    def test_configured_webhook_sends(self):
        calls = []

        def fake_post(url, payload, headers):
            calls.append((url, payload["to"], headers["Authorization"]))
            return 200

        adapter = messaging.WebhookAdapter("https://sms.example/send", "tok", fake_post)
        res = messaging.dispatch([messaging.Message("017", "hi")], adapter)
        self.assertEqual(res.sent, 1)
        self.assertEqual(calls[0][2], "Bearer tok")

    def test_payslip_text_is_bilingual(self):
        text = messaging.payslip_text("Rahim", "Nov 2026", "52,563.33")
        self.assertIn("Rahim", text)
        self.assertIn("নিট বেতন", text)


class AnomalyTests(unittest.TestCase):
    def test_net_jump_threshold(self):
        self.assertIsNone(anomaly.check_net_jump(55000, 50000))
        self.assertEqual(anomaly.check_net_jump(80000, 50000)["rule"], "net_pay_jump")

    def test_tds_mismatch(self):
        self.assertIsNone(anomaly.check_tds(2137, 2136.67))
        self.assertEqual(anomaly.check_tds(2100, 2136.67)["rule"], "tds_mismatch")

    def test_duplicate_bank_and_review(self):
        slips = [
            {"employee": "E1", "net_pay": 50000, "previous_net": 50000, "tds": 0, "expected_tds": 0,
             "present_days": 22, "working_days": 22, "bank_ac_no": "123"},
            {"employee": "E2", "net_pay": 50000, "previous_net": 50000, "tds": 0, "expected_tds": 0,
             "present_days": 0, "working_days": 22, "bank_ac_no": "123"},
        ]
        rules = sorted(f["rule"] for f in anomaly.review(slips))
        self.assertEqual(rules, ["duplicate_bank_account", "no_attendance"])


if __name__ == "__main__":
    unittest.main()
