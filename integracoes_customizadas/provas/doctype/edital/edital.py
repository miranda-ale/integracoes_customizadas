# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate, today


class Edital(Document):
	def validate(self):
		self.validar_etapas()
		self.validar_datas()
		self.validar_candidatos_duplicados()
	
	def on_update(self):
		"""Sincroniza campo edital nos Job Applicants vinculados."""
		self.sincronizar_edital_candidatos()
	
	def sincronizar_edital_candidatos(self):
		"""Atualiza campo edital em todos os Job Applicants da tabela candidatos."""
		if not self.candidatos:
			return
		
		for candidato in self.candidatos:
			if candidato.job_applicant:
				try:
					# Usa set_value para evitar carregar o documento inteiro
					frappe.db.set_value(
						"Job Applicant",
						candidato.job_applicant,
						"edital",
						self.name,
						update_modified=False
					)
				except Exception:
					pass  # Campo pode não existir se Custom Field não foi criado
		
		frappe.db.commit()
	
	def validar_etapas(self):
		"""Valida que há pelo menos uma etapa definida."""
		if not self.etapas or len(self.etapas) == 0:
			frappe.throw(_("É necessário definir pelo menos uma etapa do processo seletivo."))
		
		# Sincroniza o campo ordem com idx para compatibilidade
		for etapa in self.etapas:
			etapa.ordem = etapa.idx
	
	def validar_datas(self):
		"""Valida as datas do edital."""
		if self.data_publicacao and self.data_encerramento:
			if getdate(self.data_encerramento) < getdate(self.data_publicacao):
				frappe.throw(_("A data de encerramento não pode ser anterior à data de publicação."))
	
	def validar_candidatos_duplicados(self):
		"""Valida que não há candidatos duplicados."""
		if self.candidatos:
			candidatos = [c.job_applicant for c in self.candidatos]
			if len(candidatos) != len(set(candidatos)):
				frappe.throw(_("Não é permitido incluir o mesmo candidato mais de uma vez."))
	
	def get_etapas_ordenadas(self):
		"""Retorna as etapas ordenadas pelo idx (ordem de inserção)."""
		return sorted(self.etapas, key=lambda x: x.idx)
	
	def get_proxima_etapa(self, etapa_atual):
		"""Retorna a próxima etapa após a etapa atual."""
		etapas_ordenadas = self.get_etapas_ordenadas()
		
		for i, etapa in enumerate(etapas_ordenadas):
			if etapa.interview_round == etapa_atual:
				if i + 1 < len(etapas_ordenadas):
					return etapas_ordenadas[i + 1].interview_round
		
		return None
	
	def importar_candidatos_da_vaga(self):
		"""Importa todos os candidatos da vaga vinculada."""
		if not self.job_opening:
			frappe.throw(_("É necessário selecionar uma vaga para importar candidatos."))
		
		# Busca candidatos da vaga
		candidatos_existentes = [c.job_applicant for c in self.candidatos] if self.candidatos else []
		
		job_applicants = frappe.get_all(
			"Job Applicant",
			filters={
				"job_title": self.job_opening,
				"status": ["not in", ["Rejected"]]
			},
			fields=["name", "applicant_name", "email_id"]
		)
		
		novos = 0
		primeira_etapa = self.get_etapas_ordenadas()[0].interview_round if self.etapas else None
		
		for ja in job_applicants:
			if ja.name not in candidatos_existentes:
				self.append("candidatos", {
					"job_applicant": ja.name,
					"etapa_atual": primeira_etapa,
					"status_candidato": "Inscrito"
				})
				
				# Atualiza o Job Applicant com o edital
				try:
					job_applicant_doc = frappe.get_doc("Job Applicant", ja.name)
					job_applicant_doc.edital = self.name
					job_applicant_doc.save(ignore_permissions=True)
				except Exception:
					pass  # Ignora erro se não conseguir atualizar
				
				novos += 1
		
		self.save()
		
		frappe.msgprint(
			_("{0} candidato(s) importado(s) da vaga.").format(novos),
			indicator="green",
			title=_("Importação Concluída")
		)
		
		return {"importados": novos}
	
	def avancar_candidatos(self, candidatos_ids, proxima_etapa, criar_interview=True, enviar_email=True):
		"""Avança candidatos selecionados para a próxima etapa.
		
		Args:
			candidatos_ids: Lista de job_applicant names
			proxima_etapa: Interview Round da próxima etapa
			criar_interview: Se deve criar Interview automaticamente
			enviar_email: Se deve enviar email de notificação
		
		Returns:
			Dict com resultado da operação
		"""
		if not candidatos_ids:
			frappe.throw(_("Selecione pelo menos um candidato para avançar."))
		
		if not proxima_etapa:
			frappe.throw(_("Selecione a próxima etapa."))
		
		# Verifica se a etapa existe no edital
		etapas_validas = [e.interview_round for e in self.etapas]
		if proxima_etapa not in etapas_validas:
			frappe.throw(_("A etapa selecionada não faz parte deste edital."))
		
		avancados = 0
		erros = []
		interviews_criados = []
		
		for candidato_item in self.candidatos:
			if candidato_item.job_applicant in candidatos_ids:
				try:
					# Atualiza a etapa atual do candidato
					candidato_item.etapa_atual = proxima_etapa
					candidato_item.status_candidato = "Em Avaliação"
					
					# Cria Interview se solicitado
					if criar_interview:
						interview = self.criar_interview_para_candidato(
							candidato_item.job_applicant,
							proxima_etapa
						)
						candidato_item.interview = interview.name
						interviews_criados.append(interview.name)
					
					# Envia email se solicitado
					if enviar_email:
						self.enviar_email_avanco_etapa(
							candidato_item.job_applicant,
							proxima_etapa
						)
					
					avancados += 1
					
				except Exception as e:
					erros.append(
						_("Erro ao avançar candidato {0}: {1}").format(
							candidato_item.job_applicant, str(e)
						)
					)
		
		# Salva o documento
		self.save()
		
		# Monta mensagem de resultado
		mensagem = _("{0} candidato(s) avançado(s) para a etapa '{1}'.").format(
			avancados, proxima_etapa
		)
		
		if interviews_criados:
			mensagem += "\n" + _("{0} Interview(s) criado(s).").format(len(interviews_criados))
		
		if erros:
			mensagem += "\n\n" + _("Erros:") + "\n" + "\n".join(erros)
			frappe.msgprint(mensagem, indicator="orange", title=_("Avanço Parcial"))
		else:
			frappe.msgprint(mensagem, indicator="green", title=_("Sucesso"))
		
		return {
			"avancados": avancados,
			"interviews_criados": interviews_criados,
			"erros": erros
		}
	
	def criar_interview_para_candidato(self, job_applicant, interview_round):
		"""Cria um Interview para o candidato na etapa especificada."""
		# Verifica se já existe Interview para este candidato nesta etapa
		interview_existente = frappe.db.exists(
			"Interview",
			{
				"job_applicant": job_applicant,
				"interview_round": interview_round,
				"docstatus": ["!=", 2]
			}
		)
		
		if interview_existente:
			return frappe.get_doc("Interview", interview_existente)
		
		# Busca dados do candidato
		job_applicant_doc = frappe.get_doc("Job Applicant", job_applicant)
		
		# Busca dados do Interview Round
		interview_round_doc = frappe.get_doc("Interview Round", interview_round)
		
		# Busca dados da etapa no edital para obter data e horários
		etapa_edital = None
		for etapa in self.etapas:
			if etapa.interview_round == interview_round:
				etapa_edital = etapa
				break
		
		# Cria novo Interview
		interview = frappe.new_doc("Interview")
		interview.interview_round = interview_round
		interview.job_applicant = job_applicant
		interview.designation = interview_round_doc.designation or self.designation
		interview.job_opening = self.job_opening
		interview.resume_link = job_applicant_doc.resume_link
		interview.status = "Pending"  # Status inicial explícito
		
		# Define data e horários da etapa se disponíveis
		if etapa_edital:
			if etapa_edital.data_prevista:
				interview.scheduled_on = etapa_edital.data_prevista
			if etapa_edital.hora_inicio:
				interview.from_time = etapa_edital.hora_inicio
			if etapa_edital.hora_fim:
				interview.to_time = etapa_edital.hora_fim
		
		# Vincula o edital ao Interview (via Custom Field)
		interview.edital = self.name
		
		# Adiciona entrevistadores do Interview Round
		if interview_round_doc.interviewers:
			for interviewer in interview_round_doc.interviewers:
				interview.append("interview_details", {
					"interviewer": interviewer.user
				})
		
		interview.insert(ignore_permissions=True)
		
		# Atualiza Job Applicant com o edital e status
		job_applicant_doc.status = "Replied"
		job_applicant_doc.edital = self.name
		job_applicant_doc.save(ignore_permissions=True)
		
		return interview
	
	def enviar_email_avanco_etapa(self, job_applicant, proxima_etapa):
		"""Envia email de notificação ao candidato sobre avanço de etapa."""
		try:
			job_applicant_doc = frappe.get_doc("Job Applicant", job_applicant)
			
			if not job_applicant_doc.email_id:
				return
			
			# Busca dados da etapa
			etapa_doc = frappe.get_doc("Interview Round", proxima_etapa)
			
			# Prepara conteúdo do email
			subject = _("Processo Seletivo - Avanço de Etapa - {0}").format(self.titulo)
			
			message = _("""
				<p>Prezado(a) {0},</p>
				
				<p>Informamos que você foi aprovado(a) e avançou para a próxima etapa do processo seletivo.</p>
				
				<p><strong>Edital:</strong> {1}</p>
				<p><strong>Vaga:</strong> {2}</p>
				<p><strong>Próxima Etapa:</strong> {3}</p>
				
				<p>Em breve você receberá mais informações sobre a data e local da próxima etapa.</p>
				
				<p>Atenciosamente,<br>
				Equipe de Recrutamento</p>
			""").format(
				job_applicant_doc.applicant_name,
				self.titulo,
				self.job_opening,
				etapa_doc.round_name
			)
			
			frappe.sendmail(
				recipients=[job_applicant_doc.email_id],
				subject=subject,
				message=message,
				reference_doctype=self.doctype,
				reference_name=self.name
			)
			
		except Exception as e:
			frappe.log_error(
				f"Erro ao enviar email para {job_applicant}: {str(e)}",
				"Edital - Envio de Email"
			)
	
	def gerar_publicacao_blog(self):
		"""Gera uma publicação no blog com o conteúdo do edital."""
		if not self.titulo or not self.descricao:
			frappe.throw(_("O edital precisa ter título e descrição para gerar a publicação."))
		
		# Verifica se o Blog Post DocType existe
		if not frappe.db.exists("DocType", "Blog Post"):
			frappe.throw(_("O módulo de Blog não está disponível nesta instalação."))
		
		# Verifica se já existe um blog post para este edital
		blog_existente = frappe.db.exists(
			"Blog Post",
			{"title": self.titulo}
		)
		
		if blog_existente:
			frappe.throw(
				_("Já existe uma publicação com este título. Edite a publicação existente: {0}").format(
					blog_existente
				)
			)
		
		# Busca ou cria um Blog Category
		blog_category = frappe.db.get_value("Blog Category", {"name": "Editais"}, "name")
		if not blog_category:
			# Cria categoria se não existir
			category = frappe.new_doc("Blog Category")
			category.title = "Editais"
			category.insert(ignore_permissions=True)
			blog_category = category.name
		
		# Busca um Blogger (autor)
		blogger = frappe.db.get_value("Blogger", {}, "name")
		if not blogger:
			# Cria um blogger padrão se não existir
			new_blogger = frappe.new_doc("Blogger")
			new_blogger.full_name = "Recursos Humanos"
			new_blogger.short_name = "RH"
			new_blogger.insert(ignore_permissions=True)
			blogger = new_blogger.name
		
		# Cria o Blog Post
		blog_post = frappe.new_doc("Blog Post")
		blog_post.title = self.titulo
		blog_post.blog_category = blog_category
		blog_post.blogger = blogger
		blog_post.content_type = "Rich Text"
		blog_post.content = self.descricao
		blog_post.published = 1 if self.status == "Publicado" else 0
		
		blog_post.insert(ignore_permissions=True)
		
		frappe.msgprint(
			_("Publicação criada com sucesso: {0}").format(
				frappe.utils.get_link_to_form("Blog Post", blog_post.name)
			),
			indicator="green",
			title=_("Blog Post Criado")
		)
		
		return blog_post.name


@frappe.whitelist()
def importar_candidatos(edital_name):
	"""Método whitelisted para importar candidatos da vaga."""
	doc = frappe.get_doc("Edital", edital_name)
	return doc.importar_candidatos_da_vaga()


@frappe.whitelist()
def avancar_candidatos(edital_name, candidatos, proxima_etapa, criar_interview=1, enviar_email=1):
	"""Método whitelisted para avançar candidatos de etapa."""
	import json
	
	if isinstance(candidatos, str):
		candidatos = json.loads(candidatos)
	
	criar_interview = bool(int(criar_interview))
	enviar_email = bool(int(enviar_email))
	
	doc = frappe.get_doc("Edital", edital_name)
	return doc.avancar_candidatos(candidatos, proxima_etapa, criar_interview, enviar_email)


@frappe.whitelist()
def gerar_blog(edital_name):
	"""Método whitelisted para gerar publicação no blog."""
	doc = frappe.get_doc("Edital", edital_name)
	return doc.gerar_publicacao_blog()


@frappe.whitelist()
def get_candidatos_por_etapa(edital_name, etapa=None):
	"""Retorna candidatos agrupados por etapa."""
	doc = frappe.get_doc("Edital", edital_name)
	
	resultado = {}
	for candidato in doc.candidatos:
		etapa_atual = candidato.etapa_atual or "Sem Etapa"
		if etapa_atual not in resultado:
			resultado[etapa_atual] = []
		
		resultado[etapa_atual].append({
			"job_applicant": candidato.job_applicant,
			"applicant_name": candidato.applicant_name,
			"status_candidato": candidato.status_candidato,
			"nota": candidato.nota,
			"interview": candidato.interview
		})
	
	if etapa:
		return resultado.get(etapa, [])
	
	return resultado
