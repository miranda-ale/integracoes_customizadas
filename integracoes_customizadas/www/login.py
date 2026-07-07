import frappe
from frappe.apps import get_default_path
from frappe.website.utils import get_home_page

no_cache = True


def get_context(context):
	redirect_to = frappe.local.request.args.get("redirect-to")

	if frappe.session.user != "Guest":
		if not redirect_to:
			if frappe.session.data.user_type == "Website User":
				redirect_to = get_default_path() or get_home_page()
			else:
				redirect_to = get_default_path() or "/app"

		if redirect_to != "login":
			frappe.local.flags.redirect_location = redirect_to
			raise frappe.Redirect

	context.no_header = True
	context.full_width = True
	return context
