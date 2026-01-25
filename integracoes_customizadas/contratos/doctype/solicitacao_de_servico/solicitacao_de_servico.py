import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


class SolicitacaodeServico(Document):
	def validate(self):
		if not self.data_solicitacao:
			self.data_solicitacao = nowdate()

		if self.data_inicio and self.data_solicitacao:
			if getdate(self.data_inicio) < getdate(self.data_solicitacao):
				frappe.throw("A Data de Início não pode ser anterior à Data da Solicitação.")
