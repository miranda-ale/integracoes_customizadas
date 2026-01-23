# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AplicacaoProva(Document):
	def validate(self):
		self.validar_candidatos()
	
	def validar_candidatos(self):
		"""Valida que há pelo menos um candidato."""
		if not self.candidatos or len(self.candidatos) == 0:
			frappe.throw(_("É necessário informar pelo menos um candidato."))
		
		# Verifica duplicatas
		candidatos = [c.job_applicant for c in self.candidatos]
		if len(candidatos) != len(set(candidatos)):
			frappe.throw(_("Não é permitido incluir o mesmo candidato mais de uma vez."))
	
	def vincular_prova_aos_candidatos(self):
		"""Vincula a prova aos Interviews dos candidatos selecionados."""
		if not self.prova:
			frappe.throw(_("É necessário selecionar uma prova."))
		
		if not self.candidatos:
			frappe.throw(_("É necessário informar pelo menos um candidato."))
		
		prova_doc = frappe.get_doc("Prova", self.prova)
		tipo_interview_esperado = "Prova de Conhecimentos Gerais e Específicos"
		
		vinculados = 0
		erros = []
		
		for candidato_item in self.candidatos:
			try:
				# Busca ou cria Interview do tipo correto para o candidato
				interview = self.buscar_ou_criar_interview(
					candidato_item.job_applicant,
					tipo_interview_esperado,
					prova_doc.designation
				)
				
				# Vincula a prova ao Interview
				if hasattr(interview, "prova"):
					interview.prova = self.prova
					interview.save(ignore_permissions=True)
					
					# Atualiza o campo interview no item do candidato
					candidato_item.interview = interview.name
					vinculados += 1
				else:
					erros.append(
						_("Interview {0} não possui o campo 'prova'. Verifique se o Custom Field foi criado.")
						.format(interview.name)
					)
			
			except Exception as e:
				erros.append(
					_("Erro ao vincular prova para candidato {0}: {1}")
					.format(candidato_item.job_applicant, str(e))
				)
		
		# Salva o documento atualizado
		self.save(ignore_permissions=True)
		
		# Mostra mensagem de resultado
		mensagem = _("{0} candidato(s) vinculado(s) com sucesso.").format(vinculados)
		if erros:
			mensagem += "\n\n" + _("Erros encontrados:") + "\n" + "\n".join(erros)
			frappe.msgprint(mensagem, indicator="orange", title=_("Vinculação Parcial"))
		else:
			frappe.msgprint(mensagem, indicator="green", title=_("Sucesso"))
		
		return {"vinculados": vinculados, "erros": erros}
	
	def buscar_ou_criar_interview(self, job_applicant, interview_type, designation=None):
		"""Busca ou cria um Interview do tipo especificado para o Job Applicant."""
		# Busca um Interview Round do tipo correto
		interview_round = frappe.db.get_value(
			"Interview Round",
			{"interview_type": interview_type},
			"name"
		)
		
		if not interview_round:
			# Cria um Interview Round padrão se não existir
			interview_round = self.criar_interview_round_padrao(interview_type, designation)
		
		# Busca um Interview existente com o mesmo Interview Round e Job Applicant
		interview_existente = frappe.db.exists(
			"Interview",
			{
				"job_applicant": job_applicant,
				"interview_round": interview_round,
				"docstatus": ["!=", 2]  # Não cancelado
			}
		)
		
		if interview_existente:
			return frappe.get_doc("Interview", interview_existente)
		
		# Cria novo Interview
		job_applicant_doc = frappe.get_doc("Job Applicant", job_applicant)
		
		interview = frappe.new_doc("Interview")
		interview.interview_round = interview_round
		interview.job_applicant = job_applicant
		interview.designation = designation or job_applicant_doc.designation
		interview.resume_link = job_applicant_doc.resume_link
		interview.job_opening = job_applicant_doc.job_title
		
		interview.insert(ignore_permissions=True)
		
		return interview
	
	def criar_interview_round_padrao(self, interview_type, designation=None):
		"""Cria um Interview Round padrão se não existir."""
		# Verifica se o Interview Type existe
		if not frappe.db.exists("Interview Type", interview_type):
			# Cria o Interview Type se não existir
			interview_type_doc = frappe.new_doc("Interview Type")
			interview_type_doc.name = interview_type
			interview_type_doc.insert(ignore_permissions=True)
		
		round_name = f"Prova de Conhecimentos - {designation or 'Geral'}"
		
		# Verifica se já existe um Interview Round com esse tipo
		existing_round = frappe.db.get_value(
			"Interview Round",
			{"interview_type": interview_type},
			"name"
		)
		
		if existing_round:
			return existing_round
		
		# Cria novo Interview Round
		interview_round = frappe.new_doc("Interview Round")
		interview_round.round_name = round_name
		interview_round.interview_type = interview_type
		if designation:
			interview_round.designation = designation
		interview_round.insert(ignore_permissions=True)
		
		return interview_round.name


@frappe.whitelist()
def vincular_prova(docname):
	"""Método whitelisted para vincular prova aos candidatos."""
	doc = frappe.get_doc("Aplicacao Prova", docname)
	return doc.vincular_prova_aos_candidatos()
