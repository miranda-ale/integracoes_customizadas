# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class Prova(Document):
	def before_insert(self):
		self.gerar_identificador()

	def validate(self):
		self.calcular_total_pontos()
		self.validar_interview_tipo()
		self.validar_questoes_designation()
		self.validar_questoes_duplicadas()
		self.validar_ordem_questoes()

	def gerar_identificador(self):
		"""Gera identificador único para a prova no formato PRV-YYYYMMDD-XXXX."""
		if not self.identificador:
			dt = now_datetime()
			# Conta quantas provas foram criadas hoje para gerar sequencial
			hoje = dt.strftime("%Y-%m-%d")
			count = frappe.db.count(
				"Prova",
				filters={
					"creation": [">=", f"{hoje} 00:00:00"],
					"creation": ["<=", f"{hoje} 23:59:59"],
				},
			)
			seq = str(count + 1).zfill(4)
			self.identificador = f"PRV-{dt.strftime('%Y%m%d')}-{seq}"

	def calcular_total_pontos(self):
		"""Calcula o total de pontos da prova baseado nos pesos das questões."""
		self.total_pontos = sum(q.peso or 0 for q in self.questoes)

	def validar_interview_tipo(self):
		"""Valida que o Interview vinculado é do tipo correto."""
		if not self.interview:
			return

		interview = frappe.get_doc("Interview", self.interview)

		# Verifica se o Interview é do tipo "Prova de Conhecimentos Gerais e Específicos"
		tipo_esperado = "Prova de Conhecimentos Gerais e Específicos"
		if hasattr(interview, "interview_type") and interview.interview_type != tipo_esperado:
			frappe.throw(
				_(
					"O Interview {0} deve ser do tipo '{1}' para ser vinculado a uma prova. "
					"Tipo atual: {2}"
				).format(self.interview, tipo_esperado, interview.interview_type)
			)

	def validar_questoes_designation(self):
		"""Valida que todas as questões são aplicáveis ao cargo da prova.

		Considera disciplinas gerais (aplicavel_a_todos) e específicas.
		"""
		if not self.designation:
			return

		for item in self.questoes:
			questao = frappe.get_doc("Questao", item.questao)
			disciplina = frappe.get_doc("Disciplina", questao.disciplina)

			# Se a disciplina é aplicável a todos, a questão pode ser usada
			if disciplina.aplicavel_a_todos:
				continue

			# Se a disciplina é específica, verifica se o cargo está na disciplina
			if not disciplina.is_aplicavel_a_designation(self.designation):
				frappe.throw(
					_(
						"A questão {0} pertence à disciplina '{1}' que não é aplicável ao cargo {2}."
					).format(item.questao, questao.disciplina, self.designation)
				)

			# Verifica também se a questão tem o cargo na sua lista de designations
			designations_questao = questao.get_designations()
			if self.designation not in designations_questao:
				frappe.throw(
					_(
						"A questão {0} não é aplicável ao cargo {1}. "
						"Cargos aplicáveis: {2}"
					).format(
						item.questao,
						self.designation,
						", ".join(designations_questao),
					)
				)

	def validar_questoes_duplicadas(self):
		"""Valida que não há questões duplicadas na prova."""
		questoes = [q.questao for q in self.questoes]
		if len(questoes) != len(set(questoes)):
			frappe.throw(_("Não é permitido incluir a mesma questão mais de uma vez na prova."))

	def validar_ordem_questoes(self):
		"""Valida e ajusta a ordem das questões."""
		ordens = [q.ordem for q in self.questoes]
		if len(ordens) != len(set(ordens)):
			# Auto-ajusta a ordem se houver duplicatas
			for idx, questao in enumerate(self.questoes, start=1):
				questao.ordem = idx

	def get_questoes_completas(self):
		"""Retorna as questões completas com todos os dados para o print format."""
		questoes_completas = []
		for item in sorted(self.questoes, key=lambda x: x.ordem):
			questao = frappe.get_doc("Questao", item.questao)
			questoes_completas.append(
				{
					"ordem": item.ordem,
					"peso": item.peso,
					"tipo": questao.tipo,
					"disciplina": questao.disciplina,
					"dificuldade": questao.dificuldade,
					"enunciado": questao.enunciado,
					"alternativas": questao.alternativas if questao.tipo == "Objetiva" else [],
					"resposta_esperada": questao.resposta_esperada if questao.tipo == "Discursiva" else None,
				}
			)
		return questoes_completas

	def get_gabarito(self):
		"""Retorna o gabarito da prova para questões objetivas."""
		gabarito = []
		for item in sorted(self.questoes, key=lambda x: x.ordem):
			questao = frappe.get_doc("Questao", item.questao)
			if questao.tipo == "Objetiva":
				resposta = questao.get_resposta_correta()
				gabarito.append({"ordem": item.ordem, "resposta": resposta})
		return gabarito

	def get_interview_info(self):
		"""Retorna informações do Interview vinculado."""
		if not self.interview:
			return None
		return frappe.get_doc("Interview", self.interview)
