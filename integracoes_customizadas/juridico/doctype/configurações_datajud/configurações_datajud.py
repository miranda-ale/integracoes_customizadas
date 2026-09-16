import frappe
from frappe import _
from frappe.model.document import Document


class ConfiguraçõesDataJud(Document):
	def validate(self):
		if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
			frappe.throw(_("Somente administradores podem alterar a chave do DataJud."), frappe.PermissionError)
