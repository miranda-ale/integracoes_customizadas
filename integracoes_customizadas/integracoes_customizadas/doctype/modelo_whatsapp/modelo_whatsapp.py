import frappe
from frappe import _
from frappe.model.document import Document
from jinja2 import TemplateSyntaxError

from integracoes_customizadas.whatsapp.modelos import _ENV, completar_variantes, variantes_ativas
from integracoes_customizadas.whatsapp.roteador import MIN_VARIANTES


class ModeloWhatsApp(Document):
	def before_insert(self):
		# Modelo criado por código (semente de outro app) já nasce com as redações conhecidas do título.
		completar_variantes(self)

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
		for variante in self.variantes or []:
			try:
				_ENV.from_string(variante.mensagem or "")
			except TemplateSyntaxError as exc:
				frappe.throw(_("Erro de sintaxe na variante {0}: {1}").format(variante.idx, exc))
		self.validar_minimo_de_variantes()

	def validar_minimo_de_variantes(self):
		"""Toda notificação de WhatsApp precisa de ao menos 10 variantes ativas (manifesto do clm, seção 7a)."""
		if not self.ativo:
			return
		ativas = len(variantes_ativas(self))
		if ativas < MIN_VARIANTES:
			frappe.throw(
				_(
					"O Modelo WhatsApp {0} precisa de ao menos {1} variantes ativas na tabela de variantes; tem {2}."
				).format(self.titulo or self.name, MIN_VARIANTES, ativas),
				title=_("Variantes insuficientes"),
			)
