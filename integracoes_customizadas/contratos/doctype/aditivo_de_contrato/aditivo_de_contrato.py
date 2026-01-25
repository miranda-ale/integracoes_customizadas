import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class AditivodeContrato(Document):
	def validate(self):
		if self.data_inicio and self.data_fim:
			if getdate(self.data_fim) < getdate(self.data_inicio):
				frappe.throw("A data de término não pode ser anterior à data de início.")
