import frappe


def get_context(context):
	# The check-in page lives in the Desk now, so the left nav is the Desk's.
	frappe.local.flags.redirect_location = "/app/reckon-hrms-checkin"
	raise frappe.Redirect
