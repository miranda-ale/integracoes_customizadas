# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
import random
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class Prova(Document):
	def before_insert(self):
		self.gerar_identificador()

	def validate(self):
		self.verificar_custom_field_interview()
		self.calcular_total_pontos()
		self.validar_questoes_designation()
		self.validar_questoes_duplicadas()
		self.validar_ordem_questoes()

	def verificar_custom_field_interview(self):
		"""Verifica se o Custom Field 'prova' existe no DocType Interview."""
		if not frappe.db.exists("DocType", "Interview"):
			return

		custom_field_exists = frappe.db.exists(
			"Custom Field",
			{"dt": "Interview", "fieldname": "prova"}
		)

		if not custom_field_exists:
			# Tenta criar o campo automaticamente
			try:
				from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
				
				custom_fields = {
					"Interview": [
						{
							"fieldname": "prova",
							"fieldtype": "Link",
							"label": "Prova",
							"options": "Prova",
							"insert_after": "interview_round",
							"depends_on": "eval:doc.interview_type=='Prova de Conhecimentos Gerais e Específicos'",
							"description": "Prova vinculada a este Interview",
						}
					]
				}

				create_custom_fields(custom_fields, update=True)
				frappe.db.commit()
				
				frappe.msgprint(
					_("Custom Field 'prova' foi criado automaticamente no DocType 'Interview'."),
					indicator="blue",
					title=_("Campo Criado")
				)
			except Exception as e:
				frappe.log_error(
					f"Erro ao criar Custom Field 'prova' automaticamente: {str(e)}",
					"Prova - Verificação Custom Field"
				)
				# Não bloqueia o salvamento, apenas registra o erro

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

	def validar_questoes_designation(self):
		"""Valida que todas as questões são aplicáveis ao cargo da prova.

		Considera disciplinas gerais (aplicavel_a_todos) e específicas.
		O cargo é obtido do Edital vinculado.
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
			if designations_questao and self.designation not in designations_questao:
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

	def get_edital_info(self):
		"""Retorna informações do Edital vinculado."""
		if not self.edital:
			return None
		return frappe.get_doc("Edital", self.edital)


@frappe.whitelist()
def get_questoes_disponiveis(prova_name=None, designation=None, disciplina=None, tipo=None):
	"""Retorna lista de questões disponíveis para seleção na prova.
	
	Args:
		prova_name: Nome da prova (para excluir questões já adicionadas)
		designation: Cargo para filtrar questões aplicáveis
		disciplina: Disciplina para filtrar
		tipo: Tipo de questão (Objetiva/Discursiva)
	
	Returns:
		Lista de questões com informações resumidas
	"""
	filters = {"ativo": 1}
	
	# Filtros opcionais
	if disciplina:
		filters["disciplina"] = disciplina
	if tipo:
		filters["tipo"] = tipo
	
	# Busca questões
	questoes = frappe.get_all(
		"Questao",
		filters=filters,
		fields=["name", "tipo", "disciplina", "dificuldade", "enunciado"],
		order_by="modified desc"
	)
	
	# Se houver prova, exclui questões já adicionadas
	questoes_ja_adicionadas = []
	if prova_name:
		prova = frappe.get_doc("Prova", prova_name)
		questoes_ja_adicionadas = [q.questao for q in prova.questoes]
	
	# Filtra questões aplicáveis ao cargo (se fornecido)
	resultado = []
	for questao in questoes:
		if questao.name in questoes_ja_adicionadas:
			continue
		
		# Verifica se a questão é aplicável ao cargo
		if designation:
			questao_doc = frappe.get_doc("Questao", questao.name)
			disciplina_doc = frappe.get_doc("Disciplina", questao.disciplina)
			
			# Se a disciplina é aplicável a todos, OK
			if disciplina_doc.aplicavel_a_todos:
				pass
			# Se a disciplina não é aplicável a todos, verifica se o cargo está na lista
			elif not disciplina_doc.is_aplicavel_a_designation(designation):
				continue
			
			# Verifica se a questão tem o cargo na sua lista de designations
			designations_questao = questao_doc.get_designations()
			if designations_questao and designation not in designations_questao:
				continue
		
		# Limita o tamanho do enunciado para preview
		enunciado_preview = questao.enunciado
		if enunciado_preview and len(enunciado_preview) > 200:
			enunciado_preview = enunciado_preview[:200] + "..."
		
		resultado.append({
			"name": questao.name,
			"tipo": questao.tipo,
			"disciplina": questao.disciplina,
			"dificuldade": questao.dificuldade,
			"enunciado": enunciado_preview,
			"enunciado_completo": questao.enunciado
		})
	
	return resultado


@frappe.whitelist()
def gerar_questoes_automaticas(prova_name, designation, configuracoes):
	"""Gera questões automaticamente baseado em configurações de disciplinas e quantidades.
	
	Args:
		prova_name: Nome da prova
		designation: Cargo da prova
		configuracoes: Lista de dicionários com:
			- disciplina: Nome da disciplina
			- quantidade: Quantidade de questões desejada
			- dificuldade: Dificuldade (Aleatória/Fácil/Média/Difícil)
	
	Returns:
		Dict com:
			- questoes_selecionadas: Lista de nomes de questões selecionadas
			- total_adicionadas: Total de questões adicionadas
			- avisos: Lista de avisos (se houver)
	"""
	if not designation:
		frappe.throw(_("É necessário informar o cargo da prova para gerar questões."))
	
	# Obtém questões já adicionadas
	questoes_ja_adicionadas = []
	if prova_name:
		prova = frappe.get_doc("Prova", prova_name)
		questoes_ja_adicionadas = [q.questao for q in prova.questoes]
	
	questoes_selecionadas = []
	avisos = []
	
	# Processa cada configuração
	for config in configuracoes:
		disciplina = config.get("disciplina")
		quantidade = int(config.get("quantidade", 1))
		dificuldade = config.get("dificuldade", "Aleatória")
		
		if not disciplina:
			continue
		
		# Busca questões disponíveis da disciplina
		filters = {
			"ativo": 1,
			"disciplina": disciplina
		}
		
		# Filtra por dificuldade se não for "Aleatória"
		if dificuldade != "Aleatória":
			filters["dificuldade"] = dificuldade
		
		questoes_disponiveis = frappe.get_all(
			"Questao",
			filters=filters,
			fields=["name", "tipo", "disciplina", "dificuldade"]
		)
		
		# Filtra questões aplicáveis ao cargo
		questoes_aplicaveis = []
		for questao in questoes_disponiveis:
			# Exclui questões já adicionadas
			if questao.name in questoes_ja_adicionadas:
				continue
			
			# Verifica se a questão é aplicável ao cargo
			questao_doc = frappe.get_doc("Questao", questao.name)
			disciplina_doc = frappe.get_doc("Disciplina", disciplina)
			
			# Se a disciplina é aplicável a todos, OK
			if disciplina_doc.aplicavel_a_todos:
				questoes_aplicaveis.append(questao.name)
			# Se a disciplina não é aplicável a todos, verifica se o cargo está na lista
			elif disciplina_doc.is_aplicavel_a_designation(designation):
				# Verifica se a questão tem o cargo na sua lista de designations
				designations_questao = questao_doc.get_designations()
				if not designations_questao or designation in designations_questao:
					questoes_aplicaveis.append(questao.name)
		
		# Seleciona aleatoriamente a quantidade solicitada
		if len(questoes_aplicaveis) < quantidade:
			avisos.append(
				_(
					"Disciplina '{0}': solicitadas {1} questões, mas apenas {2} disponíveis. "
					"Foram adicionadas {2} questão(ões)."
				).format(disciplina, quantidade, len(questoes_aplicaveis))
			)
			quantidade = len(questoes_aplicaveis)
		
		if questoes_aplicaveis:
			# Seleciona aleatoriamente
			random.shuffle(questoes_aplicaveis)
			questoes_selecionadas.extend(questoes_aplicaveis[:quantidade])
		else:
			avisos.append(
				_("Disciplina '{0}': nenhuma questão disponível aplicável ao cargo '{1}'.").format(
					disciplina, designation
				)
			)
	
	return {
		"questoes_selecionadas": questoes_selecionadas,
		"total_adicionadas": len(questoes_selecionadas),
		"avisos": avisos
	}
