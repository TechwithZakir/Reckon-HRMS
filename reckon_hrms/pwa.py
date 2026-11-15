"""Reckon HRMS on the Frappe HR mobile app (the installable web app at /hrms).

The app is Frappe HR's own and is left as it is. Reckon HRMS puts its own name and icons on the page that
loads it: the title, the install name and icon, and the words and logo the app draws, so staff install and
open "Reckon HRMS". It runs as an ``after_request`` hook on /hrms only, so a Frappe HR update changes nothing here.
"""

from __future__ import annotations

import re

ASSETS = "/assets/reckon_hrms/pwa"
MANIFEST = f"{ASSETS}/manifest.json"
BRAND = "Reckon HRMS"

_SPLASH = re.compile(r"\s*<link\s+rel=\"apple-touch-startup-image\"[^>]*>", re.S)


def is_app_path(path: str) -> bool:
    return path == "/hrms" or path.startswith("/hrms/")


def rebrand_html(html: str) -> str:
    """The mobile app's page with Reckon HRMS's name, icons and manifest."""
    html = html.replace("<title>Frappe HR</title>", f"<title>{BRAND}</title>")
    html = html.replace('name="apple-mobile-web-app-title" content="Frappe HR"', f'name="apple-mobile-web-app-title" content="{BRAND}"')
    html = html.replace("/assets/hrms/frontend/manifest.webmanifest", MANIFEST)
    html = html.replace("/assets/hrms/manifest/favicon-196.png", f"{ASSETS}/favicon-196.png")
    html = html.replace("/assets/hrms/manifest/apple-icon-180.png", f"{ASSETS}/apple-icon-180.png")
    html = _SPLASH.sub("", html)  # Frappe HR's iPhone launch screens
    if f"{ASSETS}/rebrand.js" not in html:
        html = html.replace("</head>", f'<script src="{ASSETS}/rebrand.js" defer></script></head>', 1)
    return html


def rebrand_response(response, request=None) -> None:
    """``after_request`` hook."""
    try:
        if request is None or not is_app_path(request.path) or response.status_code != 200:
            return
        if "text/html" not in (response.content_type or ""):
            return
        response.set_data(rebrand_html(response.get_data(as_text=True)))
    except Exception:  # noqa: BLE001  # never break the app over its branding
        import frappe

        frappe.log_error(title="Reckon HRMS mobile app rebrand")
