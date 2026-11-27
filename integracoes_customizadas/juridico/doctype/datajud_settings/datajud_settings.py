import frappe
from frappe import _
from frappe.model.document import Document


class DataJudSettings(Document):
	def validate(self):
		if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
			frappe.throw(
				_("Somente administradores podem alterar a chave do DataJud."), frappe.PermissionError
			)
		if self.has_value_changed("api_key") and self.circuito_tipo_falha == "Autenticação":
			# Trocar a chave é o único jeito de sair da pausa por erro de autenticação; reabre o
			# circuito imediatamente e deixa a próxima execução confirmar com um health check.
			self.circuito_aberto = 0
			self.circuito_tipo_falha = None
			self.circuito_motivo = None
			self.circuito_aberto_em = None
			self.circuito_nivel_backoff = 0
			self.circuito_proxima_tentativa = None
			self.falhas_consecutivas = 0
			self.tipo_ultima_falha = None
