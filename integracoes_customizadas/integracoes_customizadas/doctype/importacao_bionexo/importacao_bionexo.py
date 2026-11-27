# Copyright (c) 2026, BHCL and contributors
# For license information, please see license.txt
"""Importação do "Relatório geral de PDC" do Bionexo para um Pedido de Cotação (Request for Quotation).

Ao salvar, o PDF é lido (``bionexo/import_pdf.py``) e os itens, fornecedores e cotações são relacionados ao
Pedido de Cotação. Ao submeter, gera um Supplier Quotation submetido por fornecedor que cotou e, para os itens
com status "Confirmado", uma Purchase Order em rascunho por fornecedor.
"""

import re
from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate

from integracoes_customizadas.bionexo.import_pdf import parse_relatorio
from integracoes_customizadas.bionexo.importacao import (
	fornecedor_por_cnpj,
	fornecedor_por_nome,
	material_requests_da_rfq,
	normalizar_cnpj,
	rfqs_da_material_request,
)

STATUS_CONFIRMADO = "Confirmado"
NAO_IDENTIFICADO = "Não identificado"
NAO_CADASTRADO = "Não cadastrado"
ENCONTRADO_PELO_NOME = "Encontrado pelo nome"


class ImportacaoBionexo(Document):
	def validate(self):
		if self.arquivo_pdf and (self.is_new() or self.has_value_changed("arquivo_pdf") or not self.itens):
			self.analisar_pdf()
		self.validar_vinculos()
		self.resolver()
		self.validar_duplicidade()
		self.status = "Pendências" if self.pendencias() else "Pronto"

	@frappe.whitelist()
	def reanalisar(self):
		"""Relê o PDF (descarta escolhas manuais) e salva."""
		self.analisar_pdf()
		self.save()

	def conteudo_pdf(self) -> bytes:
		return frappe.get_doc("File", {"file_url": self.arquivo_pdf}).get_content()

	def analisar_pdf(self):
		try:
			dados = parse_relatorio(self.conteudo_pdf())
		except Exception as erro:
			frappe.throw(_("Não foi possível ler o relatório do Bionexo: {0}").format(erro))

		self.id_cotacao_bionexo = dados["id_cotacao"]
		self.titulo_bionexo = (dados["titulo"] or "")[:140]
		self.data_cotacao = dados["data_criacao"]
		self.forma_pagamento = dados["forma_pagamento"]
		self.observacoes_bionexo = dados["observacoes"]

		self.set("itens", [])
		self.set("cotacoes", [])
		for item in dados["itens"]:
			self.append(
				"itens",
				{
					"seq": item["seq"],
					"codigo_bionexo": item["codigo"],
					"descricao": item["descricao"],
					"unidade": item["unidade"],
					"qtd_solicitada": item["qtd_solicitada"],
				},
			)
			for resposta in item["respostas"]:
				self.append(
					"cotacoes",
					{
						"seq": item["seq"],
						"codigo_bionexo": item["codigo"],
						"nome_bionexo": resposta["fornecedor"],
						"cnpj": resposta["cnpj"],
						"qty": resposta["qty"],
						"rate": resposta["rate"],
						"amount": resposta["amount"],
						"status_bionexo": resposta["status"],
						"item_fornecedor": resposta["item_fornecedor"],
						"marca": resposta["marca"],
						"embalagem": resposta["embalagem"],
						"observacao": resposta["observacao"],
						"confirmado_por": resposta["confirmado_por"],
						"justificativa": resposta["justificativa"],
						"data_confirmacao": resposta.get("data_confirmacao"),
					},
				)

		sem_cnpj = sorted({c.nome_bionexo for c in self.cotacoes if not c.cnpj})
		if sem_cnpj:
			frappe.throw(
				_("Fornecedores sem CNPJ na tabela de participantes do relatório: {0}").format(
					", ".join(sem_cnpj)
				)
			)

		cotados = {normalizar_cnpj(c.cnpj) for c in self.cotacoes}
		self.set("fornecedores", [])
		for participante in dados["participantes"]:
			if normalizar_cnpj(participante["cnpj"]) not in cotados:
				continue
			self.append(
				"fornecedores",
				{
					"nome_bionexo": participante["nome"],
					"cnpj": participante["cnpj"],
					"email": participante["email"],
					"telefone": participante["telefone"],
					"contato": participante["contato"],
					"pagamento": participante["pagamento"],
					"faturamento_minimo": participante["faturamento_minimo"],
					"validade": participante["validade"],
					"entrega": participante["entrega"],
				},
			)

		if not self.request_for_quotation:
			self.identificar_rfq(dados)

	def identificar_rfq(self, dados):
		"""RFQ citada em Observações/Título (o XML exportado grava o nome dela) ou com o mesmo ID Bionexo."""
		texto = "\n".join([dados["observacoes"] or "", dados["titulo"] or ""])
		for nome in re.findall(r"[A-Z0-9]+(?:-[A-Z0-9]+){2,}", texto):
			if frappe.db.get_value("Request for Quotation", nome, "docstatus") == 1:
				self.request_for_quotation = nome
				return
			if not self.material_request and frappe.db.get_value("Material Request", nome, "docstatus") == 1:
				self.material_request = nome
		if self.id_cotacao_bionexo:
			self.request_for_quotation = frappe.db.get_value(
				"Request for Quotation",
				{"custom_id_bionexo": self.id_cotacao_bionexo, "docstatus": 1},
				"name",
			)

	def validar_vinculos(self):
		if not self.request_for_quotation and self.material_request:
			self.validar_solicitacao()
			existentes = rfqs_da_material_request(self.material_request)
			if len(existentes) == 1:
				self.request_for_quotation = existentes[0]
		if not self.request_for_quotation:
			return
		rfq = frappe.db.get_value(
			"Request for Quotation", self.request_for_quotation, ["docstatus", "company"], as_dict=True
		)
		if rfq.docstatus != 1:
			frappe.throw(
				_("O Pedido de Cotação {0} precisa estar enviado.").format(self.request_for_quotation)
			)
		self.empresa_da_referencia(rfq.company, _("Pedido de Cotação"), self.request_for_quotation)

		solicitacoes = material_requests_da_rfq(self.request_for_quotation)
		if not self.material_request and len(solicitacoes) == 1:
			self.material_request = solicitacoes[0]
		elif self.material_request and self.material_request not in solicitacoes:
			frappe.throw(
				_("O Pedido de Cotação {0} não pertence à Solicitação de Compras {1}.").format(
					self.request_for_quotation, self.material_request
				)
			)

	def validar_solicitacao(self):
		mr = frappe.db.get_value(
			"Material Request", self.material_request, ["docstatus", "company"], as_dict=True
		)
		if not mr or mr.docstatus != 1:
			frappe.throw(
				_("A Solicitação de Compras {0} precisa estar enviada.").format(self.material_request)
			)
		self.empresa_da_referencia(mr.company, _("Solicitação de Compras"), self.material_request)

	def empresa_da_referencia(self, empresa, rotulo, nome):
		"""A empresa acompanha a referência escolhida; editada depois dela, precisa continuar igual."""
		mudou = (
			self.is_new()
			or self.has_value_changed("request_for_quotation")
			or self.has_value_changed("material_request")
		)
		if not self.company or mudou:
			self.company = empresa
		elif self.company != empresa:
			frappe.throw(
				_("A empresa {0} difere da empresa do {1} {2} ({3}).").format(
					self.company, rotulo, nome, empresa
				)
			)

	def rfq_sera_gerada(self) -> bool:
		"""Há Solicitação de Compras sem Pedido de Cotação: ele é gerado a partir do relatório ao concluir."""
		return bool(self.material_request and not self.request_for_quotation)

	def resolver(self):
		"""Relaciona itens às linhas da RFQ e fornecedores aos cadastros; propaga para as cotações."""
		# Sem Pedido de Cotação (ele será gerado), concilia com os itens da Solicitação de Compras.
		linhas_rfq = []
		if self.request_for_quotation:
			linhas_rfq = frappe.get_all(
				"Request for Quotation Item",
				filters={"parent": self.request_for_quotation},
				fields=["name", "item_code"],
				order_by="idx asc",
			)
		elif self.material_request:
			linhas_rfq = frappe.get_all(
				"Material Request Item",
				filters={"parent": self.material_request},
				fields=["name", "item_code"],
				order_by="idx asc",
			)
		por_codigo = {}
		for linha in linhas_rfq:
			por_codigo.setdefault(linha.item_code, linha.name)

		usados = set()
		for item in self.itens:
			item.rfq_item = None
			if item.ignorar:
				item.situacao = "Ignorado"
				continue
			if item.item_code not in por_codigo:
				item.item_code = self._codigo_no_erp(item.codigo_bionexo, por_codigo)
			if item.item_code in por_codigo and item.item_code not in usados:
				item.rfq_item = por_codigo[item.item_code] if self.request_for_quotation else None
				usados.add(item.item_code)
			item.situacao = "Identificado" if item.item_code in usados else NAO_IDENTIFICADO

		for fornecedor in self.fornecedores:
			if fornecedor.supplier:
				if fornecedor.situacao != ENCONTRADO_PELO_NOME:
					fornecedor.situacao = "Encontrado"
			elif supplier := fornecedor_por_cnpj(fornecedor.cnpj):
				fornecedor.supplier, fornecedor.situacao = supplier, "Encontrado"
			elif supplier := fornecedor_por_nome(fornecedor.nome_bionexo):
				fornecedor.supplier, fornecedor.situacao = supplier, ENCONTRADO_PELO_NOME
			else:
				fornecedor.situacao = NAO_CADASTRADO

		itens = {item.seq: item for item in self.itens}
		fornecedores = {normalizar_cnpj(f.cnpj): f for f in self.fornecedores}
		cotados, confirmados = defaultdict(int), defaultdict(int)
		for cotacao in self.cotacoes:
			item = itens.get(cotacao.seq)
			fornecedor = fornecedores.get(normalizar_cnpj(cotacao.cnpj))
			cotacao.item_code = item.item_code if item else None
			cotacao.rfq_item = item.rfq_item if item else None
			cotacao.supplier = fornecedor.supplier if fornecedor else None
			if fornecedor:
				cotados[fornecedor.cnpj] += 1
				confirmados[fornecedor.cnpj] += cotacao.status_bionexo == STATUS_CONFIRMADO
		for fornecedor in self.fornecedores:
			fornecedor.itens_cotados = cotados[fornecedor.cnpj]
			fornecedor.itens_confirmados = confirmados[fornecedor.cnpj]

	@staticmethod
	def _codigo_no_erp(codigo, por_codigo):
		if codigo in por_codigo:
			return codigo
		for item_code in frappe.get_all("Item", filters={"custom_código_bionexo": codigo}, pluck="name"):
			if item_code in por_codigo:
				return item_code
		return None

	def validar_duplicidade(self):
		if not self.id_cotacao_bionexo:
			return
		outra = frappe.db.get_value(
			"Importacao Bionexo",
			{"id_cotacao_bionexo": self.id_cotacao_bionexo, "docstatus": 1, "name": ["!=", self.name]},
			"name",
		)
		if outra:
			frappe.throw(
				_("A cotação {0} do Bionexo já foi importada em {1}.").format(self.id_cotacao_bionexo, outra)
			)

	def cotacoes_validas(self):
		itens_ativos = {item.seq for item in self.itens if item.situacao == "Identificado"}
		return [c for c in self.cotacoes if c.seq in itens_ativos and flt(c.rate) > 0 and flt(c.qty) > 0]

	def cotacoes_a_gerar(self):
		"""Cotações que viram Orçamento: itens confirmados dos vencedores e, se marcado, tudo dos demais."""
		validas = self.cotacoes_validas()
		vencedores = {normalizar_cnpj(c.cnpj) for c in validas if c.status_bionexo == STATUS_CONFIRMADO}
		gerar = []
		for cotacao in validas:
			if normalizar_cnpj(cotacao.cnpj) in vencedores:
				if cotacao.status_bionexo == STATUS_CONFIRMADO:
					gerar.append(cotacao)
			elif self.gerar_demais_fornecedores:
				gerar.append(cotacao)
		return gerar

	def pendencias(self) -> list[str]:
		pendencias = []
		if not self.request_for_quotation and not self.material_request:
			pendencias.append(_("Selecione a Solicitação de Compras ou o Pedido de Cotação."))
		elif not self.request_for_quotation and len(rfqs_da_material_request(self.material_request)) > 1:
			pendencias.append(_("Há mais de um Pedido de Cotação para a Solicitação: escolha um."))
		nao_identificados = [i for i in self.itens if i.situacao == NAO_IDENTIFICADO]
		if nao_identificados:
			no_erp = set(
				frappe.get_all(
					"Item",
					filters={"name": ["in", [i.codigo_bionexo for i in nao_identificados]]},
					pluck="name",
				)
			)
			pendencias.append(
				_(
					"Itens não identificados (relacione ou marque Ignorar). Os marcados com * existem no ERP, mas não estão na Solicitação/Pedido de Cotação: {0}"
				).format(
					", ".join(
						i.codigo_bionexo + ("*" if i.codigo_bionexo in no_erp else "")
						for i in nao_identificados
					)
				)
			)
		precisam = {normalizar_cnpj(c.cnpj) for c in self.cotacoes_a_gerar()}
		sem_cadastro = [
			f"{f.nome_bionexo} ({f.cnpj})"
			for f in self.fornecedores
			if not f.supplier and normalizar_cnpj(f.cnpj) in precisam
		]
		if sem_cadastro:
			pendencias.append(_("Fornecedores não cadastrados: {0}").format(", ".join(sem_cadastro)))
		if (
			(self.request_for_quotation or self.material_request)
			and self.itens
			and not self.cotacoes_a_gerar()
		):
			pendencias.append(_("Nenhuma cotação com preço para itens identificados."))
		return pendencias

	def before_submit(self):
		pendencias = self.pendencias()
		if pendencias:
			frappe.throw("<br>".join(pendencias), title=_("Resolva as pendências antes de concluir"))

		existentes = []
		for supplier in (
			sorted({c.supplier for c in self.cotacoes_a_gerar()}) if self.request_for_quotation else []
		):
			orcamento = _orcamento_existente(supplier, self.request_for_quotation)
			if orcamento:
				existentes.append(f"{supplier}: {orcamento}")
		if existentes:
			frappe.throw(
				_(
					"Já existem Orçamentos de Fornecedor para este Pedido de Cotação (cancele-os ou exclua-os antes):"
				)
				+ "<br>"
				+ "<br>".join(existentes)
			)

	def on_submit(self):
		if not self.request_for_quotation:
			self._gerar_rfq()
		rfq = frappe.get_doc("Request for Quotation", self.request_for_quotation)
		por_fornecedor = defaultdict(list)
		for cotacao in self.cotacoes_a_gerar():
			por_fornecedor[cotacao.supplier].append(cotacao)

		self._completar_rfq(rfq, por_fornecedor)
		validade = {f.supplier: f.validade for f in self.fornecedores if f.supplier}
		orcamentos, ordens = [], []
		for supplier, cotacoes in por_fornecedor.items():
			orcamento = self._criar_orcamento(rfq, supplier, cotacoes, validade.get(supplier))
			orcamentos.append(orcamento.name)
			confirmadas = [c for c in cotacoes if c.status_bionexo == STATUS_CONFIRMADO]
			if confirmadas:
				ordem = self._criar_ordem_compra(rfq, orcamento, confirmadas)
				ordens.append(ordem.name)

		self.db_set("status", "Concluído")
		frappe.msgprint(
			_("Orçamentos de Fornecedor gerados: {0}<br>Ordens de Compra em rascunho: {1}").format(
				len(orcamentos), ", ".join(_link("Purchase Order", o) for o in ordens) or _("nenhuma")
			),
			title=_("Importação concluída"),
			indicator="green",
		)

	def _gerar_rfq(self):
		"""Gera e envia o Pedido de Cotação da Solicitação de Compras com os itens identificados do relatório."""
		from erpnext.stock.doctype.material_request.material_request import make_request_for_quotation

		hoje = getdate(nowdate())
		rfq = make_request_for_quotation(self.material_request)
		por_codigo = {i.item_code: i for i in self.itens if i.situacao == "Identificado"}
		rfq.set("items", [linha for linha in rfq.items if linha.item_code in por_codigo])
		rfq.company = self.company or rfq.company
		rfq.transaction_date = self.data_cotacao or hoje
		rfq.subject = (self.titulo_bionexo or f"Bionexo {self.id_cotacao_bionexo}")[:140]
		rfq.message_for_supplier = _("Pedido de Cotação gerado a partir da cotação {0} do Bionexo.").format(
			self.id_cotacao_bionexo
		)
		for idx, linha in enumerate(rfq.items, start=1):
			linha.idx = idx
			linha.schedule_date = max(getdate(linha.schedule_date or hoje), getdate(rfq.transaction_date))
		rfq.schedule_date = min(linha.schedule_date for linha in rfq.items)
		if rfq.meta.has_field("custom_id_bionexo"):
			rfq.custom_id_bionexo = self.id_cotacao_bionexo
		rfq.insert()
		rfq.submit()

		por_item_rfq = {linha.item_code: linha.name for linha in rfq.items}
		for item in self.itens:
			if item.situacao == "Identificado":
				item.db_set("rfq_item", por_item_rfq.get(item.item_code))
		for cotacao in self.cotacoes:
			cotacao.rfq_item = por_item_rfq.get(cotacao.item_code)
			cotacao.db_set("rfq_item", cotacao.rfq_item)
		self.request_for_quotation = rfq.name
		self.db_set({"request_for_quotation": rfq.name, "rfq_gerada": 1})

	def _completar_rfq(self, rfq, por_fornecedor):
		"""O ERPNext só submete o orçamento de fornecedor presente na tabela de fornecedores da RFQ."""
		presentes = {linha.supplier for linha in rfq.suppliers}
		emails = {f.supplier: f.email for f in self.fornecedores if f.supplier}
		idx = len(rfq.suppliers)
		for supplier in por_fornecedor:
			if supplier in presentes:
				continue
			idx += 1
			linha = frappe.get_doc(
				{
					"doctype": "Request for Quotation Supplier",
					"parent": rfq.name,
					"parenttype": "Request for Quotation",
					"parentfield": "suppliers",
					"idx": idx,
					"supplier": supplier,
					"supplier_name": frappe.db.get_value("Supplier", supplier, "supplier_name"),
					"email_id": emails.get(supplier),
					"send_email": 0,
					"quote_status": "Pending",
				}
			)
			linha.db_insert()
		if (
			not rfq.get("custom_id_bionexo")
			and self.id_cotacao_bionexo
			and rfq.meta.has_field("custom_id_bionexo")
		):
			frappe.db.set_value(
				"Request for Quotation",
				rfq.name,
				"custom_id_bionexo",
				self.id_cotacao_bionexo,
				update_modified=False,
			)

	def _criar_orcamento(self, rfq, supplier, cotacoes, validade):
		from erpnext.buying.doctype.request_for_quotation.request_for_quotation import (
			make_supplier_quotation_from_rfq,
		)

		orcamento = make_supplier_quotation_from_rfq(rfq.name, for_supplier=supplier)
		por_linha = {c.rfq_item: c for c in cotacoes}
		orcamento.set("items", [i for i in orcamento.items if i.request_for_quotation_item in por_linha])
		for idx, item in enumerate(orcamento.items, start=1):
			cotacao = por_linha[item.request_for_quotation_item]
			item.idx = idx
			item.qty = flt(cotacao.qty)
			item.rate = flt(cotacao.rate)
		orcamento.transaction_date = self.data_cotacao or nowdate()
		if validade and getdate(validade) >= getdate(orcamento.transaction_date):
			orcamento.valid_till = validade
		orcamento.run_method("set_missing_values")
		orcamento.insert()
		orcamento.submit()

		for cotacao in cotacoes:
			cotacao.db_set("supplier_quotation", orcamento.name)
		return orcamento

	def _criar_ordem_compra(self, rfq, orcamento, confirmadas):
		from erpnext.buying.doctype.supplier_quotation.supplier_quotation import make_purchase_order

		itens_orcamento = {i.request_for_quotation_item: i.name for i in orcamento.items}
		linhas = [itens_orcamento[c.rfq_item] for c in confirmadas]
		ordem = make_purchase_order(orcamento.name, args={"filtered_children": linhas})
		hoje = getdate(nowdate())
		# Data da OC = quando o item foi confirmado no Bionexo (a mais recente entre os itens do fornecedor).
		confirmacoes = [getdate(c.data_confirmacao) for c in confirmadas if c.data_confirmacao]
		ordem.transaction_date = max(confirmacoes) if confirmacoes else hoje
		for item in ordem.items:
			data = None
			if item.material_request_item:
				data = frappe.db.get_value(
					"Material Request Item", item.material_request_item, "schedule_date"
				)
			data = getdate(data or rfq.schedule_date or hoje)
			item.schedule_date = max(data, getdate(ordem.transaction_date), hoje)
		ordem.schedule_date = min(item.schedule_date for item in ordem.items)
		ordem.insert()

		for cotacao in confirmadas:
			cotacao.db_set("purchase_order", ordem.name)
		return ordem

	def on_cancel(self):
		ordens = sorted({c.purchase_order for c in self.cotacoes if c.purchase_order})
		submetidas = [o for o in ordens if frappe.db.get_value("Purchase Order", o, "docstatus") == 1]
		if submetidas:
			frappe.throw(_("Cancele antes as Ordens de Compra enviadas: {0}").format(", ".join(submetidas)))
		for cotacao in self.cotacoes:
			if cotacao.purchase_order:
				cotacao.db_set("purchase_order", None)
		for ordem in ordens:
			if frappe.db.exists("Purchase Order", {"name": ordem, "docstatus": 0}):
				frappe.delete_doc("Purchase Order", ordem)
		for orcamento in sorted({c.supplier_quotation for c in self.cotacoes if c.supplier_quotation}):
			doc = frappe.get_doc("Supplier Quotation", orcamento)
			if doc.docstatus == 1:
				doc.cancel()
		if (
			self.rfq_gerada
			and frappe.db.get_value("Request for Quotation", self.request_for_quotation, "docstatus") == 1
		):
			try:
				frappe.get_doc("Request for Quotation", self.request_for_quotation).cancel()
			except frappe.LinkExistsError:
				frappe.msgprint(
					_("O Pedido de Cotação {0} tem outros documentos vinculados e foi mantido.").format(
						self.request_for_quotation
					),
					indicator="orange",
				)
		self.db_set("status", "Cancelado")


def _orcamento_existente(supplier, request_for_quotation):
	encontrado = frappe.db.sql(
		"""select sq.name from `tabSupplier Quotation` sq
		inner join `tabSupplier Quotation Item` sqi on sqi.parent = sq.name
		where sq.supplier = %s and sq.docstatus < 2 and sqi.request_for_quotation = %s
		limit 1""",
		(supplier, request_for_quotation),
	)
	return encontrado[0][0] if encontrado else None


def _link(doctype, name):
	return f'<a href="/app/{frappe.scrub(doctype).replace("_", "-")}/{name}">{name}</a>'
