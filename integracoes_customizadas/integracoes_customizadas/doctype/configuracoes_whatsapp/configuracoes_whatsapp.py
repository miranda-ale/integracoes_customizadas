from urllib.parse import urlsplit

import frappe
from frappe import _
from frappe.model.document import Document


class ConfiguracoesWhatsApp(Document):
	def validate(self):
		url = (self.server_url or "").strip().rstrip("/")
		parts = urlsplit(url)
		if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
			frappe.throw(_("Informe uma URL HTTP ou HTTPS válida, sem credenciais."))
		if parts.query or parts.fragment:
			frappe.throw(_("Informe apenas o endereço base da Evolution API, sem parâmetros."))
		self.server_url = url
		self.instance_name = (self.instance_name or "").strip()
