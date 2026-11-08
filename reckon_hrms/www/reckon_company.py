import frappe


def get_context(context):
	# Page 1 (Your company). Sign-in is required; the page calls reckon_hrms.api.setup.
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/reckon/company"
		raise frappe.Redirect
	context.no_cache = 1
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.company = frappe.defaults.get_user_default("Company") or ""
	context.title = "Your company"
