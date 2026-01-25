import frappe
from frappe.model.document import Document


class PesquisadePrecos(Document):
	def validate(self):
		if self.dispensada and not self.justificativa_dispensa:
			frappe.throw("Preencha a justificativa da dispensa da pesquisa de preços.")
