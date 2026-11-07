import frappe


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw("Sign in to check in.", frappe.PermissionError)
    context.no_cache = 1
    context.csrf_token = frappe.sessions.get_csrf_token()
    context.title = "Check in"
