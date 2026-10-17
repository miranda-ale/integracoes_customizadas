import frappe
from frappe import _
from frappe.model.document import Document
from jinja2 import TemplateSyntaxError

from integracoes_customizadas.whatsapp.modelos import _ENV


class ModeloWhatsApp(Document):
	def validate(self):
		# Erro de sintaxe Jinja aparece ao salvar, não na hora do envio.
		for campo in ("mensagem", "assunto_email", "mensagem_email"):
			texto = self.get(campo)
			if not texto:
				continue
			try:
				_ENV.from_string(texto)
			except TemplateSyntaxError as exc:
				frappe.throw(_("Erro de sintaxe em {0}: {1}").format(self.meta.get_label(campo), exc))
