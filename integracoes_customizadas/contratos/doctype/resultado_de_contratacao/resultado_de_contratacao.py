import frappe
from frappe.model.document import Document


class ResultadodeContratacao(Document):
	def validate(self):
		if self.status == "Homologado" and not self.data_homologacao:
			frappe.throw("Preencha a data de homologação para resultados homologados.")
