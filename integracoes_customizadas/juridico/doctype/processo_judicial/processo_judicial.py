# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import json
import re
from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today
from frappe.utils.data import convert_utc_to_system_timezone, get_datetime

from integracoes_customizadas.juridico import agenda


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


def _normalizar_documento(valor: str | None) -> str | None:
	"""Valida e aplica a máscara de CPF ou CNPJ (reutiliza busca_cnpj e rh_brasil); vazio vira None."""
	from busca_cnpj.cnpj import formatar_cnpj, normalizar_cnpj, validar_tax_id
	from rh_brasil.documentos import format_cpf

	base = normalizar_cnpj(valor)
	if not base:
		return None
	if len(base) not in (11, 14) or not validar_tax_id(base):
		frappe.throw(_("CPF/CNPJ inválido: {0}").format(valor))
	return format_cpf(base) if len(base) == 11 else formatar_cnpj(base)


def _normalizar_oab(valor: str | None) -> str | None:
	"""Aceita "123456/SP", "SP 123456" ou "SP-123.456" e devolve "123456/SP"; vazio vira None."""
	texto = (valor or "").strip().upper()
	if not texto:
		return None
	numero = "".join(c for c in texto if c.isdigit())
	uf = "".join(c for c in texto if c.isalpha())
	if not (1 <= len(numero) <= 6 and re.fullmatch(r"[A-Z]{2}", uf)) or re.search(r"[^0-9A-Z./\s-]", texto):
		frappe.throw(_("OAB inválida: {0}. Use o formato 123456/SP.").format(valor))
	return f"{int(numero)}/{uf}"


PROBABILIDADES_POR_GRAVIDADE = ("Provável", "Possível", "Remota")

CAMPOS_NOME_PARTE = {
	"Employee": "employee_name",
	"Customer": "customer_name",
	"Supplier": "supplier_name",
	"Terceiros": "full_name",
}


def _doctype_da_parte(tipo_parte: str | None) -> str | None:
	return "Contact" if tipo_parte == "Terceiros" else tipo_parte


class ProcessoJudicial(Document):
	def _definir_doctype_parte(self):
		self.doctype_parte = _doctype_da_parte(self.tipo_parte)
		# O Frappe valida os links (Dynamic Link) antes do validate, então as linhas precisam do doctype já aqui.
		for linha in self.get("partes") or []:
			linha.doctype_parte = _doctype_da_parte(linha.tipo_parte)

	def _em_importacao(self):
		return bool(frappe.flags.in_import or self.flags.in_import)

	def save(self, *args, **kwargs):
		self._definir_doctype_parte()
		return super().save(*args, **kwargs)

	def insert(self, *args, **kwargs):
		self._definir_doctype_parte()
		# O Frappe verifica os links antes de before_insert e validate.
		if self._em_importacao():
			# Carga em massa (Data Import): exige permissão e o identificador, sem consulta ao DataJud.
			if not kwargs.get("ignore_permissions"):
				self.check_permission("create")
			if not self.datajud_id:
				frappe.throw(_("Informe o ID DataJud para importar o processo."))
			self.flags.consulta_datajud_validada = True
		elif not self.flags.from_datajud:
			if not kwargs.get("ignore_permissions"):
				self.check_permission("create")
			from integracoes_customizadas.juridico.datajud import _preencher_ocorrencia

			consulta = (
				frappe.cache.get_value(f"datajud-rascunho:{self.consulta_token}")
				if self.consulta_token
				else None
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
		self._sincronizar_partes()
		if self.tipo_parte and self.tipo_parte not in CAMPOS_NOME_PARTE:
			frappe.throw(_("Tipo da Parte inválido."))
		if self.parte and (not self.doctype_parte or not frappe.db.exists(self.doctype_parte, self.parte)):
			frappe.throw(_("Selecione uma parte válida para o tipo informado."))
		if self.processo_relacionado and self.processo_relacionado == self.name:
			frappe.throw(_("Um processo não pode ser relacionado a si mesmo."))
		self._validar_parte()
		self._validar_classificacao()
		self._validar_advogados()
		self._calcular_provisao()
		self._calcular_financeiro()

	def on_update(self):
		agenda.sincronizar(self)

	def _validar_classificacao(self):
		"""Normaliza a classificação interna e garante pasta única por empresa."""
		for campo in ("tipo_acao", "objeto", "pasta_interna"):
			self.set(campo, (self.get(campo) or "").strip() or None)
		if self.pasta_interna and frappe.db.exists(
			"Processo Judicial",
			{"pasta_interna": self.pasta_interna, "empresa": self.empresa or "", "name": ["!=", self.name]},
		):
			frappe.throw(_("A pasta {0} já está em uso por outro processo desta empresa.").format(self.pasta_interna))

	def _validar_advogados(self):
		vistas = set()
		for linha in self.advogados:
			linha.nome = (linha.nome or "").strip()
			linha.escritorio = (linha.escritorio or "").strip() or None
			linha.oab = _normalizar_oab(linha.oab)
			if not linha.nome:
				frappe.throw(_("Linha {0}: informe o nome do advogado.").format(linha.idx))
			if linha.tipo == "Externo" and not linha.escritorio:
				frappe.throw(_("Linha {0}: informe o escritório do advogado externo.").format(linha.idx))
			if (linha.honorarios or 0) < 0:
				frappe.throw(_("Linha {0}: os honorários não podem ser negativos.").format(linha.idx))
			if linha.oab:
				if linha.oab in vistas:
					frappe.throw(_("Linha {0}: a OAB {1} já consta neste processo.").format(linha.idx, linha.oab))
				vistas.add(linha.oab)

	def _calcular_provisao(self):
		"""Provisão (CPC 25): sugerida pelos pedidos prováveis; probabilidade do processo é a do pior pedido."""
		for linha in self.pedidos:
			linha.descricao = (linha.descricao or "").strip()
			if flt(linha.valor_pedido) < 0 or flt(linha.valor_provavel) < 0:
				frappe.throw(_("Linha {0}: os valores do pedido não podem ser negativos.").format(linha.idx))
			if linha.probabilidade_perda == "Provável" and not flt(linha.valor_provavel):
				frappe.throw(_("Linha {0}: informe o valor provável do pedido com perda provável.").format(linha.idx))
		self.valor_provisionado_sugerido = sum(
			flt(linha.valor_provavel) for linha in self.pedidos if linha.probabilidade_perda == "Provável"
		)
		if self.pedidos:
			probabilidades = {linha.probabilidade_perda for linha in self.pedidos}
			self.probabilidade_perda = next(p for p in PROBABILIDADES_POR_GRAVIDADE if p in probabilidades)
		if not self.provisao_manual:
			self.valor_provisionado = self.valor_provisionado_sugerido
		if flt(self.valor_provisionado) < 0:
			frappe.throw(_("O valor provisionado não pode ser negativo."))

		anterior = self.get_doc_before_save()
		mudou = not anterior or (
			anterior.probabilidade_perda != self.probabilidade_perda
			or flt(anterior.valor_provisionado) != flt(self.valor_provisionado)
		)
		if mudou and (self.probabilidade_perda or flt(self.valor_provisionado)):
			self.data_provisao = today()

	def _calcular_financeiro(self):
		"""Valida depósitos, acordos e custas e calcula os totais; o encerramento exige resultado."""
		for tabela, rotulo in (("depositos", "depósito"), ("acordos", "acordo"), ("custas", "custa")):
			for linha in self.get(tabela):
				if flt(linha.valor) < 0:
					frappe.throw(_("Linha {0}: o valor do {1} não pode ser negativo.").format(linha.idx, rotulo))
		for linha in self.acordos:
			if linha.situacao != "Pago":
				linha.data_pagamento = None
			if (linha.parcelas or 0) < 1:
				frappe.throw(_("Linha {0}: informe ao menos uma parcela.").format(linha.idx))
		for linha in self.custas:
			if not linha.pago:
				linha.data_pagamento = None
		self.saldo_depositado = sum(flt(d.valor) for d in self.depositos if d.situacao == "Depositado")
		self.total_acordos = sum(flt(a.valor) for a in self.acordos if a.situacao != "Descumprido")
		self.total_custas = sum(flt(c.valor) for c in self.custas)

		if self.data_encerramento:
			if not self.resultado:
				frappe.throw(_("Informe o resultado do processo para registrar a data de encerramento."))
			if getdate(self.data_encerramento) > getdate(today()):
				frappe.throw(_("A data de encerramento não pode ser futura."))
			if self.data_ajuizamento and getdate(self.data_encerramento) < getdate(self.data_ajuizamento):
				frappe.throw(_("A data de encerramento não pode ser anterior ao ajuizamento."))

	def _sincronizar_partes(self):
		"""A tabela de partes é a fonte; a parte principal é espelhada nos campos de topo.

		Sem linhas, os campos de topo (importação, vincular_colaborador) geram a linha principal.
		"""
		principal = next((linha for linha in self.partes if linha.principal), None)
		anterior = self.get_doc_before_save()
		anterior_principal = (
			next((linha for linha in anterior.partes if linha.principal), None) if anterior else None
		)
		campos = (("tipo_parte", "tipo_parte"), ("parte", "parte"), ("nome", "nome_parte"), ("documento", "cpf_parte"))
		if (
			principal
			and anterior_principal
			and all(principal.get(linha) == anterior_principal.get(linha) for linha, _topo in campos)
			and any(self.get(topo) != anterior.get(topo) for _linha, topo in campos)
		):
			# Edição direta dos campos de topo (API antiga): a linha principal acompanha.
			for linha, topo in campos:
				principal.set(linha, self.get(topo))
		if not self.partes and (self.parte or self.nome_parte or self.cpf_parte):
			self.append(
				"partes",
				{
					"papel": "Reclamante",
					"tipo_parte": self.tipo_parte,
					"parte": self.parte,
					"nome": self.nome_parte,
					"documento": self.cpf_parte,
					"principal": 1,
				},
			)
		if not self.partes:
			return

		for linha in self.partes:
			if linha.tipo_parte and linha.tipo_parte not in CAMPOS_NOME_PARTE:
				frappe.throw(_("Linha {0}: Tipo da Parte inválido.").format(linha.idx))
			linha.doctype_parte = _doctype_da_parte(linha.tipo_parte)
			if linha.parte:
				if not linha.doctype_parte or not frappe.db.exists(linha.doctype_parte, linha.parte):
					frappe.throw(_("Linha {0}: selecione uma parte válida para o tipo informado.").format(linha.idx))
				linha.nome = frappe.db.get_value(
					linha.doctype_parte, linha.parte, CAMPOS_NOME_PARTE[linha.tipo_parte]
				)
			else:
				linha.nome = (linha.nome or "").strip()
			if not (linha.parte or linha.nome):
				frappe.throw(_("Linha {0}: informe a parte cadastrada ou o nome da parte.").format(linha.idx))
			linha.documento = _normalizar_documento(linha.documento)

		principais = [linha for linha in self.partes if linha.principal]
		if not principais and len(self.partes) == 1:
			principais = [self.partes[0]]
			principais[0].principal = 1
		if len(principais) != 1:
			frappe.throw(_("Marque exatamente uma parte como principal."))
		principal = principais[0]
		self.tipo_parte = principal.tipo_parte
		self.parte = principal.parte
		self.nome_parte = principal.nome
		self.cpf_parte = principal.documento
		self._definir_doctype_parte()

	def _validar_parte(self):
		"""Garante que o processo identifique a parte, com ou sem cadastro prévio."""
		self.parte_vinculada = 1 if self.parte else 0
		if self.parte:
			self.nome_parte = frappe.db.get_value(self.doctype_parte, self.parte, CAMPOS_NOME_PARTE[self.tipo_parte])
		elif self.nome_parte:
			self.nome_parte = self.nome_parte.strip()
		self.cpf_parte = _normalizar_documento(self.cpf_parte)
		if self.data_admissao and self.data_demissao and self.data_demissao < self.data_admissao:
			frappe.throw(_("A data de desligamento não pode ser anterior à admissão."))

		if self.situacao_cadastro != "Cadastrado":
			return
		if not (self.tipo_parte and self.empresa and self.polo_empresa):
			frappe.throw(_("Informe tipo da parte, empresa e polo da empresa para finalizar o cadastro."))
		if not self.parte and not (self.nome_parte and self.cpf_parte):
			frappe.throw(
				_("Informe a parte cadastrada ou, na falta dela, o nome e o CPF/CNPJ da parte.")
			)

	def _validar_dados_datajud_inalterados(self, anterior):
		campos_datajud = (
			"datajud_id",
			"numero_processo",
			"tribunal",
			"grau",
			"nivel_sigilo",
			"orgao_julgador_codigo",
			"orgao_julgador_nome",
			"orgao_julgador_codigo_municipio_ibge",
			"classe_codigo",
			"classe_nome",
			"sistema_codigo",
			"sistema_nome",
			"formato_codigo",
			"formato_nome",
			"data_ajuizamento_original",
			"data_ajuizamento",
			"data_hora_ultima_atualizacao_original",
			"data_hora_ultima_atualizacao",
			"timestamp_original",
			"timestamp",
		)
		campos_data_hora = {"data_ajuizamento", "data_hora_ultima_atualizacao", "timestamp"}
		if any(
			(
				not _data_hora_igual(self.get(campo), anterior.get(campo))
				if campo in campos_data_hora
				else self.get(campo) != anterior.get(campo)
			)
			for campo in campos_datajud
		):
			frappe.throw(_("Os dados retornados pelo DataJud não podem ser alterados manualmente."))
		for tabela, campos in (
			("assuntos", ("assunto", "codigo", "nome")),
			(
				"movimentos",
				(
					"codigo",
					"nome",
					"descricao",
					"data_hora_original",
					"data_hora",
					"orgao_julgador_codigo",
					"orgao_julgador_nome",
					"complementos_tabelados",
				),
			),
		):

			def valores(linhas):
				return [
					tuple(
						get_datetime(linha.get(campo))
						if linha.get(campo) and campo == "data_hora"
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
