"""The Frappe HR mobile app carries the Reckon HRMS name, icons and manifest."""

import json
import unittest
from pathlib import Path

from reckon_hrms import pwa

PKG = Path(__file__).resolve().parents[1] / "reckon_hrms"

PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8" />
<title>Frappe HR</title>
<meta name="apple-mobile-web-app-title" content="Frappe HR" />
<link rel="icon" type="image/png" sizes="196x196" href="/assets/hrms/manifest/favicon-196.png" />
<link rel="apple-touch-icon" href="/assets/hrms/manifest/apple-icon-180.png" />
<link
	rel="apple-touch-startup-image"
	href="/assets/hrms/manifest/apple-splash-2048-2732.jpg"
	media="(device-width: 1024px)"
/>
<link rel="apple-touch-startup-image" href="/assets/hrms/manifest/apple-splash-640-1136.jpg" media="(device-width: 320px)" />
<script type="module" src="/assets/hrms/frontend/assets/index-abc.js"></script>
<link rel="manifest" href="/assets/hrms/frontend/manifest.webmanifest"></head><body><div id="app"></div></body></html>"""


class Response:
    def __init__(self, body, status=200, content_type="text/html; charset=utf-8"):
        self.body, self.status_code, self.content_type = body, status, content_type

    def get_data(self, as_text=False):
        return self.body

    def set_data(self, value):
        self.body = value


class Request:
    def __init__(self, path):
        self.path = path


class RebrandTests(unittest.TestCase):
    def test_the_page_gets_the_reckon_hrms_name_icons_and_manifest(self):
        html = pwa.rebrand_html(PAGE)
        self.assertIn("<title>Reckon HRMS</title>", html)
        self.assertIn('name="apple-mobile-web-app-title" content="Reckon HRMS"', html)
        self.assertIn('rel="manifest" href="/assets/reckon_hrms/pwa/manifest.json"', html)
        self.assertIn("/assets/reckon_hrms/pwa/favicon-196.png", html)
        self.assertIn("/assets/reckon_hrms/pwa/apple-icon-180.png", html)
        self.assertNotIn("Frappe HR", html)
        self.assertNotIn("apple-touch-startup-image", html)  # Frappe HR's launch screens are gone
        self.assertIn("/assets/hrms/frontend/assets/index-abc.js", html)  # the app itself is untouched
        self.assertEqual(html.count("rebrand.js"), 1)
        self.assertEqual(pwa.rebrand_html(html), html)  # a second pass changes nothing

    def test_only_the_mobile_app_page_is_changed(self):
        self.assertTrue(all(pwa.is_app_path(p) for p in ("/hrms", "/hrms/attendance", "/hrms/home/leaves")))
        self.assertFalse(any(pwa.is_app_path(p) for p in ("/hrms-checkin", "/hrmsx", "/app/hrms", "/", "/assets/hrms/frontend/sw.js")))
        for response, path in ((Response(PAGE), "/hrms"), (Response(PAGE), "/hrms/leaves")):
            pwa.rebrand_response(response, Request(path))
            self.assertIn("Reckon HRMS", response.body)
        untouched = [
            (Response(PAGE), "/hrms-checkin"),
            (Response(PAGE, status=302), "/hrms"),
            (Response("{}", content_type="application/json"), "/hrms"),
        ]
        for response, path in untouched:
            before = response.body
            pwa.rebrand_response(response, Request(path))
            self.assertEqual(response.body, before)
        pwa.rebrand_response(Response(PAGE), None)  # no request: nothing happens, nothing breaks

    def test_the_manifest_and_icons_ship_with_the_app(self):
        data = json.loads((PKG / "public" / "pwa" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual((data["name"], data["short_name"], data["start_url"], data["display"]), ("Reckon HRMS", "Reckon HRMS", "/hrms", "standalone"))
        self.assertEqual(data["scope"], "/assets/hrms/frontend/")  # the scope the mobile app's own service worker uses
        for icon in data["icons"]:
            self.assertTrue((PKG / icon["src"].replace("/assets/reckon_hrms/", "public/")).exists(), icon["src"])
        for name in ("apple-icon-180.png", "favicon-196.png", "icon-192.png", "icon-512.png", "rebrand.js"):
            self.assertTrue((PKG / "public" / "pwa" / name).exists(), name)
        self.assertIn("reckon_hrms.pwa.rebrand_response", (PKG / "hooks.py").read_text(encoding="utf-8"))

    def test_the_script_renames_the_words_the_app_draws(self):
        script = (PKG / "public" / "pwa" / "rebrand.js").read_text(encoding="utf-8")
        for needle in ("Frappe HR", "Reckon HRMS", "MutationObserver", "icon-192.png"):
            self.assertIn(needle, script)


if __name__ == "__main__":
    unittest.main()
