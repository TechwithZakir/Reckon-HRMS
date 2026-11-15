"""ZKTeco device sync: address safety, response reading and punch parsing (no Frappe needed)."""

import unittest
from datetime import datetime

from reckon_hrms import device_sync as zk


def resolver(*ips):
    return lambda host, port: [(None, None, None, None, (ip, 0)) for ip in ips]


class AddressSafetyTests(unittest.TestCase):
    def test_only_public_addresses_are_allowed(self):
        for ip in ("8.8.8.8", "103.12.34.56", "2606:4700:4700::1111"):
            self.assertTrue(zk.is_public_address(ip), ip)
        for ip in ("127.0.0.1", "10.0.0.5", "192.168.1.20", "172.16.0.9", "169.254.169.254", "0.0.0.0", "100.64.1.1", "::1", "fe80::1", "::ffff:10.0.0.1", "224.0.0.1", "not-an-ip"):
            self.assertFalse(zk.is_public_address(ip), ip)

    def test_hosts_that_are_or_resolve_to_internal_addresses_are_refused(self):
        zk.assert_public_host("103.12.34.56")
        zk.assert_public_host("biotime.example.com", resolver("93.184.216.34"))
        for host in ("localhost", "", "127.0.0.1", "192.168.0.10", "printer.local", "db.internal", "[::1]"):
            with self.assertRaises(ValueError, msg=host):
                zk.assert_public_host(host, resolver("8.8.8.8"))
        with self.assertRaises(ValueError):  # a public name that points inside
            zk.assert_public_host("sneaky.example.com", resolver("10.1.2.3"))
        with self.assertRaises(ValueError):  # one internal answer among public ones is enough to refuse
            zk.assert_public_host("mixed.example.com", resolver("8.8.8.8", "127.0.0.1"))

        def unresolvable(host, port):
            raise OSError("no such host")

        with self.assertRaises(ValueError):
            zk.assert_public_host("nope.example.com", unresolvable)

    def test_base_url(self):
        self.assertEqual(zk.base_url("103.12.34.56", 8080), "http://103.12.34.56:8080")
        self.assertEqual(zk.base_url("example.com", None, True), "https://example.com:443")
        self.assertEqual(zk.base_url("2606:4700:4700::1111", 80), "http://[2606:4700:4700::1111]:80")
        for port in (0, 70000):
            with self.assertRaises(ValueError):
                zk.base_url("example.com", port)


class ResponseTests(unittest.TestCase):
    def test_every_response_shape_gives_the_rows_and_the_next_page(self):
        rows = [{"id": 1}]
        self.assertEqual(zk.normalise_response(rows), (rows, None))
        self.assertEqual(zk.normalise_response({"data": rows, "count": 1}), (rows, None))
        self.assertEqual(zk.normalise_response({"results": rows, "next": "http://x/?page=2"}), (rows, "http://x/?page=2"))
        self.assertEqual(zk.normalise_response({"results": None}), ([], None))
        self.assertEqual(zk.normalise_response("nonsense"), ([], None))

    def test_a_transaction_is_read_into_one_punch(self):
        parsed = zk.parse_transaction({"emp_code": " 1007 ", "punch_time": "2026-11-16 09:03:12", "punch_state": "0", "terminal_alias": "Gate", "id": 55})
        self.assertEqual(parsed, {"code": "1007", "time": datetime(2026, 11, 16, 9, 3, 12), "log_type": "IN", "device": "Gate", "id": "55"})
        self.assertEqual(zk.checkin_device_label(parsed), "Gate (ZKTeco-55)")
        out = zk.parse_transaction({"emp_code": "9", "punch_time": "2026-11-16T18:00:00Z", "punch_state": "1", "terminal_sn": "SN123"})
        self.assertEqual((out["log_type"], out["device"], out["time"].hour), ("OUT", "SN123", 18))
        self.assertEqual(zk.checkin_device_label(out), "SN123")
        self.assertEqual(zk.log_type("0", "Check Out"), "OUT")
        for bad in ({"punch_time": "2026-11-16 09:00:00"}, {"emp_code": "1"}, {"emp_code": "1", "punch_time": "yesterday"}, "text", None):
            self.assertIsNone(zk.parse_transaction(bad), bad)

    def test_authorisation_headers(self):
        self.assertEqual(zk.auth_headers("JWT", "abc")["Authorization"], "JWT abc")
        self.assertEqual(zk.AUTH_SCHEMES[0], "Bearer")  # what the original app uses is tried first


class WiringTests(unittest.TestCase):
    def test_the_device_is_company_owned_scheduled_and_in_the_menu(self):
        from pathlib import Path

        from reckon_hrms import constants, menu

        self.assertIn("HRMS Attendance Device", constants.TENANT_OWNED_DOCTYPES)  # tenant scoping applies
        self.assertIn("HRMS Attendance Device", constants.DESK_DOCTYPES)
        labels = [item[1] for _group, items in menu.MENU for item in items if len(item) > 1]
        self.assertIn("HRMS Attendance Device", labels)
        pkg = Path(__file__).resolve().parents[1] / "reckon_hrms"
        hooks = (pkg / "hooks.py").read_text(encoding="utf-8")
        self.assertIn("hrms_attendance_device.run_due_devices", hooks)
        code = (pkg / "reckon_hrms" / "doctype" / "hrms_attendance_device" / "hrms_attendance_device.py").read_text(encoding="utf-8")
        self.assertIn("allow_redirects=False", code)  # no following a redirect to an internal address
        self.assertIn('{"company": company, **extra}', code)  # employees are matched inside the device's company only
        self.assertIn('doc.check_permission("write")', code)
        import json

        doc = json.loads((pkg / "reckon_hrms" / "doctype" / "hrms_attendance_device" / "hrms_attendance_device.json").read_text(encoding="utf-8"))
        fields = {f["fieldname"]: f for f in doc["fields"]}
        self.assertEqual((fields["password"]["fieldtype"], fields["token"]["fieldtype"]), ("Password", "Password"))  # stored encrypted
        self.assertEqual(fields["company"]["reqd"], 1)


if __name__ == "__main__":
    unittest.main()
