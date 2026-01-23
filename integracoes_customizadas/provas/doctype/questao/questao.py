# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Questao(Document):
	def validate(self):
		self.validate_alternativas()
		self.validate_resposta_discursiva()
		self.validate_designations_disciplina()

	def validate_alternativas(self):
		"""Valida alternativas para questões objetivas."""
		if self.tipo == "Objetiva":
			if not self.alternativas or len(self.alternativas) < 2:
				frappe.throw(_("Questões objetivas devem ter pelo menos 2 alternativas."))

			# Verifica se há exatamente uma alternativa correta
			corretas = [alt for alt in self.alternativas if alt.correta]
			if len(corretas) == 0:
				frappe.throw(_("Questões objetivas devem ter uma alternativa marcada como correta."))
			if len(corretas) > 1:
				frappe.throw(_("Questões objetivas devem ter apenas uma alternativa correta."))

			# Verifica letras duplicadas
			letras = [alt.letra for alt in self.alternativas]
			if len(letras) != len(set(letras)):
				frappe.throw(_("Não é permitido repetir letras nas alternativas."))

	def validate_resposta_discursiva(self):
		"""Valida resposta esperada para questões discursivas."""
		if self.tipo == "Discursiva":
			if not self.resposta_esperada:
				frappe.throw(_("Questões discursivas devem ter uma resposta esperada."))

	def validate_designations_disciplina(self):
		"""Valida que os cargos da questão são compatíveis com a disciplina.

		- Se a disciplina é aplicável a todos: qualquer cargo é válido (e não é obrigatório)
		- Se a disciplina é específica: os cargos da questão devem estar
		  contidos nos cargos da disciplina e são obrigatórios
		"""
		if not self.disciplina:
			return

		disciplina = frappe.get_doc("Disciplina", self.disciplina)

		# Se a disciplina é aplicável a todos, não exige cargos
		if disciplina.aplicavel_a_todos:
			# Se houver cargos preenchidos, limpa (opcional, mas não necessário)
			return

		# Se a disciplina não é aplicável a todos, exige pelo menos um cargo
		if not self.designations or len(self.designations) == 0:
			frappe.throw(
				_(
					"A disciplina '{0}' não é aplicável a todos os cargos. "
					"É necessário informar pelo menos um cargo aplicável."
				).format(self.disciplina)
			)

		# Obtém os cargos da disciplina
		cargos_disciplina = disciplina.get_designations()
		if not cargos_disciplina:
			return

		# Verifica se todos os cargos da questão estão na disciplina
		for item in self.designations:
			if item.designation not in cargos_disciplina:
				frappe.throw(
					_(
						"O cargo '{0}' não é válido para a disciplina '{1}'. "
						"Cargos permitidos: {2}"
					).format(
						item.designation,
						self.disciplina,
						", ".join(cargos_disciplina),
					)
				)

	def get_designations(self):
		"""Retorna lista de designations associadas a esta questão."""
		return [d.designation for d in self.designations]

	def get_resposta_correta(self):
		"""Retorna a alternativa correta para questões objetivas."""
		if self.tipo == "Objetiva":
			for alt in self.alternativas:
				if alt.correta:
					return alt.letra
		return None
