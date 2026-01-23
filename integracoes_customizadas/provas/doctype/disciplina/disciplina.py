# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Disciplina(Document):
	def validate(self):
		self.validate_designations()

	def validate_designations(self):
		"""Valida que disciplinas específicas tenham pelo menos um cargo."""
		if not self.aplicavel_a_todos:
			if not self.designations or len(self.designations) == 0:
				frappe.throw(
					_("Disciplinas não aplicáveis a todos os cargos devem ter pelo menos um cargo específico.")
				)

			# Verifica duplicatas
			designations = [d.designation for d in self.designations]
			if len(designations) != len(set(designations)):
				frappe.throw(_("Não é permitido repetir cargos na disciplina."))

	def is_aplicavel_a_designation(self, designation):
		"""Verifica se a disciplina é aplicável a um cargo específico."""
		if self.aplicavel_a_todos:
			return True
		return designation in [d.designation for d in self.designations]

	def get_designations(self):
		"""Retorna lista de designations aplicáveis ou None se for geral."""
		if self.aplicavel_a_todos:
			return None
		return [d.designation for d in self.designations]
