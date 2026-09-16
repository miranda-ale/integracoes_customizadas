# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import json
from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import convert_utc_to_system_timezone, get_datetime


def _datajud_datetime(value: str | None, label: str, *, ajuizamento: bool = False) -> datetime | None:
	"""Derive a Frappe local datetime without changing the original API value."""
	if not value:
		return None

	try:
		if ajuizamento and value.isdigit() and len(value) == 14:
			return datetime.strptime(value, "%Y%m%d%H%M%S")

		parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
		if parsed.tzinfo is None:
			raise ValueError("timezone missing")
		return convert_utc_to_system_timezone(parsed).replace(tzinfo=None)
	except ValueError:
		frappe.throw(_("DataJud: valor inválido para {0}: {1}").format(label, value))


def _data_hora_igual(atual, anterior):
	"""Compara datas do formulário e do banco independentemente da representação."""
	return (get_datetime(atual) if atual else None) == (get_datetime(anterior) if anterior else None)


class ProcessoJudicial(Document):
	def insert(self, *args, **kwargs):
		# O Frappe verifica os links antes de before_insert e validate.
		if not self.flags.from_datajud:
			if not kwargs.get("ignore_permissions"):
				self.check_permission("create")
			from integracoes_customizadas.juridico.datajud import _preencher_ocorrencia

			consulta = (
				frappe.cache.get_value(f"datajud-rascunho:{self.consulta_token}")
				if self.consulta_token else None
			)
			if not consulta or consulta["usuario"] != frappe.session.user:
				frappe.throw(_("A consulta ao DataJud expirou. Consulte o processo novamente."))
			if frappe.db.exists("Processo Judicial", {"datajud_id": consulta["identificador"]}):
				frappe.throw(_("Este processo já foi cadastrado. Abra o registro existente."))
			_preencher_ocorrencia(self, consulta["identificador"], consulta["fonte"])
			self.consulta_token = None
			self.flags.consulta_datajud_validada = True
		return super().insert(*args, **kwargs)

	def validate(self):
		if not self.flags.from_datajud:
			anterior = self.get_doc_before_save()
			if not anterior:
				if not self.flags.consulta_datajud_validada:
					frappe.throw(_("O processo deve ser consultado no DataJud antes do cadastro."))
			else:
				self._validar_dados_datajud_inalterados(anterior)
		else:
			self._atualizar_dados_datajud()

		if not self.situacao_cadastro:
			self.situacao_cadastro = "Rascunho"
		if not self.status_processo:
			self.status_processo = "Em andamento"
		if self.tipo_parte and self.tipo_parte not in ("Employee", "Customer", "Supplier"):
			frappe.throw(_("Tipo da Parte inválido."))
		if self.parte and (not self.tipo_parte or not frappe.db.exists(self.tipo_parte, self.parte)):
			frappe.throw(_("Selecione uma parte válida para o tipo informado."))
		campos_nome = {"Employee": "employee_name", "Customer": "customer_name", "Supplier": "supplier_name"}
		self.nome_parte = (
			frappe.db.get_value(self.tipo_parte, self.parte, campos_nome[self.tipo_parte])
			if self.parte else None
		)
		if self.situacao_cadastro == "Cadastrado" and not (self.tipo_parte and self.parte and self.empresa):
			frappe.throw(_("Informe tipo da parte, parte e empresa para finalizar o cadastro."))

	def _validar_dados_datajud_inalterados(self, anterior):
		campos_datajud = (
			"datajud_id", "numero_processo", "tribunal", "grau", "nivel_sigilo",
			"orgao_julgador_codigo", "orgao_julgador_nome",
			"orgao_julgador_codigo_municipio_ibge", "classe_codigo", "classe_nome",
			"sistema_codigo", "sistema_nome", "formato_codigo", "formato_nome",
			"data_ajuizamento_original", "data_ajuizamento",
			"data_hora_ultima_atualizacao_original", "data_hora_ultima_atualizacao",
			"timestamp_original", "timestamp",
		)
		campos_data_hora = {"data_ajuizamento", "data_hora_ultima_atualizacao", "timestamp"}
		if any(
			(
				not _data_hora_igual(self.get(campo), anterior.get(campo))
				if campo in campos_data_hora else self.get(campo) != anterior.get(campo)
			)
			for campo in campos_datajud
		):
			frappe.throw(_("Os dados retornados pelo DataJud não podem ser alterados manualmente."))
		for tabela, campos in (
			("assuntos", ("assunto", "codigo", "nome")),
			("movimentos", ("codigo", "nome", "data_hora_original", "data_hora",
				"orgao_julgador_codigo", "orgao_julgador_nome", "complementos_tabelados")),
		):
			def valores(linhas):
				return [
					tuple(
						get_datetime(linha.get(campo)) if linha.get(campo) and campo == "data_hora"
						else linha.get(campo)
						for campo in campos
					)
					for linha in linhas
				]

			atual = valores(self.get(tabela))
			original = valores(anterior.get(tabela))
			if atual != original:
				frappe.throw(_("Os dados retornados pelo DataJud não podem ser alterados manualmente."))

	def _atualizar_dados_datajud(self):
		self.data_ajuizamento = _datajud_datetime(
			self.data_ajuizamento_original, "dataAjuizamento", ajuizamento=True
		)
		self.data_hora_ultima_atualizacao = _datajud_datetime(
			self.data_hora_ultima_atualizacao_original, "dataHoraUltimaAtualizacao"
		)
		self.timestamp = _datajud_datetime(self.timestamp_original, "@timestamp")

		for movimento in self.movimentos:
			movimento.data_hora = _datajud_datetime(movimento.data_hora_original, "movimentos[].dataHora")
			complementos = movimento.complementos_tabelados
			if complementos is None or complementos == "":
				continue
			try:
				if isinstance(complementos, str):
					complementos = json.loads(complementos)
				if not isinstance(complementos, list):
					raise ValueError("expected a JSON array")
			except (TypeError, ValueError):
				frappe.throw(_("DataJud: complementosTabelados deve ser uma lista JSON."))
			movimento.complementos_tabelados = json.dumps(complementos, ensure_ascii=False)
		self.movimentos.sort(key=lambda movimento: movimento.data_hora or datetime.min, reverse=True)
		for indice, movimento in enumerate(self.movimentos, start=1):
			movimento.idx = indice
