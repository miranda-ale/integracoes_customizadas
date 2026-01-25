import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class EditaldeContratacao(Document):
	def validate(self):
		if self.data_publicacao and self.data_limite_proposta:
			if getdate(self.data_limite_proposta) < getdate(self.data_publicacao):
				frappe.throw("O prazo de envio da proposta não pode ser anterior à data de publicação.")

		if self.data_publicacao and self.data_limite_documentacao:
			if getdate(self.data_limite_documentacao) < getdate(self.data_publicacao):
				frappe.throw("O prazo de documentação não pode ser anterior à data de publicação.")
