# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import sanitize_html, strip_html
from frappe.model.document import Document


class Questao(Document):
	def validate(self):
		self.set_preview_fields()
		self.validate_alternativas()
		self.validate_resposta_discursiva()
		self.validate_designations_disciplina()

	def set_preview_fields(self):
		enunciado_html = sanitize_html(self.enunciado or "", always_sanitize=True)
		preview_html_parts = [
			"<div class='questao-preview'>",
			f"<div class='questao-enunciado'>{enunciado_html}</div>",
		]

		preview_text_parts = [strip_html(self.enunciado or "").strip()]

		if self.tipo == "Objetiva":
			preview_html_parts.append("<div class='questao-alternativas'>")
			preview_html_parts.append("<ol class='questao-alternativas-list'>")

			alternativas = sorted(self.alternativas or [], key=lambda alt: (alt.letra or ""))
			for alt in alternativas:
				texto_html = sanitize_html(alt.texto or "", always_sanitize=True)
				preview_html_parts.append(
					f"<li><strong>{alt.letra})</strong> {texto_html}</li>"
				)
				texto_plain = strip_html(alt.texto or "").strip()
				preview_text_parts.append(f"{alt.letra}) {texto_plain}".strip())

			preview_html_parts.append("</ol>")
			preview_html_parts.append("</div>")

		elif self.tipo == "Discursiva":
			resposta_html = sanitize_html(self.resposta_esperada or "", always_sanitize=True)
			preview_html_parts.append(
				"<div class='questao-resposta'>"
				"<strong>Resposta esperada:</strong> "
				f"{resposta_html}"
				"</div>"
			)
			resposta_plain = strip_html(self.resposta_esperada or "").strip()
			if resposta_plain:
				preview_text_parts.append(f"Resposta esperada: {resposta_plain}")

		preview_html_parts.append("</div>")

		self.preview_html = "".join(preview_html_parts)
		self.preview_text = "\n".join([part for part in preview_text_parts if part])

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
