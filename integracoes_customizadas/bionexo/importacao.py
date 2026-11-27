"""Apoio à Importacao Bionexo: vínculos RFQ/Solicitação, fornecedor por CNPJ e cadastro rápido de fornecedor."""

import json
import re

import frappe
from frappe import _


def normalizar_cnpj(cnpj: str | None) -> str:
	return re.sub(r"[^0-9A-Z]", "", (cnpj or "").upper())


def fornecedor_por_cnpj(cnpj: str) -> str | None:
	"""Supplier com o CNPJ completo (filial incluída), ignorando a máscara; ativos primeiro."""
	base = normalizar_cnpj(cnpj)
	if not base:
		return None
	encontrado = frappe.db.sql(
		"""select name from `tabSupplier`
		where replace(replace(replace(replace(upper(tax_id), '.', ''), '/', ''), '-', ''), ' ', '') = %s
		order by disabled asc, creation asc limit 1""",
		base,
	)
	return encontrado[0][0] if encontrado else None


def fornecedor_por_nome(nome: str) -> str | None:
	"""Fornecedor ativo de mesmo nome cujo tax_id não é um CNPJ (há cadastros com o nome no tax_id).

	Nunca casa com um fornecedor que tem CNPJ válido: esse seria outra empresa ou outra filial.
	"""
	from integracoes_customizadas.bionexo.import_pdf import chave_nome

	chave = chave_nome(nome)
	if not chave:
		return None
	candidatos = [
		s.name
		for s in frappe.get_all(
			"Supplier", filters={"disabled": 0}, fields=["name", "supplier_name", "tax_id"]
		)
		if len(normalizar_cnpj(s.tax_id)) != 14 and chave in (chave_nome(s.supplier_name), chave_nome(s.name))
	]
	return candidatos[0] if len(candidatos) == 1 else None


def material_requests_da_rfq(request_for_quotation: str) -> list[str]:
	return sorted(
		set(
			frappe.get_all(
				"Request for Quotation Item",
				filters={"parent": request_for_quotation, "material_request": ["is", "set"]},
				pluck="material_request",
			)
		)
	)


def rfqs_da_material_request(material_request: str) -> list[str]:
	"""Pedidos de Cotação enviados que referenciam a Solicitação de Compras."""
	return sorted(
		set(
			frappe.get_all(
				"Request for Quotation Item",
				filters={"material_request": material_request, "docstatus": 1},
				pluck="parent",
			)
		)
	)


def motivo_rfq_indisponivel(
	request_for_quotation: str, id_cotacao: str | None, importacao: str | None
) -> str | None:
	"""Por que a RFQ não pode ser desta cotação do Bionexo (None se pode).

	Uma RFQ já marcada com outro ID Bionexo, ou já usada por outra importação de outra cotação, é de outra rodada
	de compra: o relatório que a cita foi copiado de uma cotação anterior no Bionexo.
	"""
	id_rfq = None
	if frappe.get_meta("Request for Quotation").has_field("custom_id_bionexo"):
		id_rfq = frappe.db.get_value("Request for Quotation", request_for_quotation, "custom_id_bionexo")
	if id_rfq and id_cotacao and str(id_rfq) != str(id_cotacao):
		return _("vinculado à cotação {0} do Bionexo").format(id_rfq)
	for outra in frappe.get_all(
		"Importacao Bionexo",
		filters={
			"request_for_quotation": request_for_quotation,
			"docstatus": ["<", 2],
			"name": ["!=", importacao or ""],
		},
		fields=["name", "id_cotacao_bionexo"],
	):
		if outra.id_cotacao_bionexo and outra.id_cotacao_bionexo != id_cotacao:
			return _("já importado em {0} (cotação {1} do Bionexo)").format(
				outra.name, outra.id_cotacao_bionexo
			)
	return None


def itens_do_relatorio_no_erp(itens: list[dict]) -> dict[str, float]:
	"""{item_code: quantidade solicitada} dos itens do relatório (código do ERP ou custom_código_bionexo)."""
	codigos = {item["codigo"]: item.get("qtd_solicitada") or 0 for item in itens if item.get("codigo")}
	if not codigos:
		return {}
	no_erp = {
		codigo: codigos[codigo]
		for codigo in frappe.get_all("Item", filters={"name": ["in", list(codigos)]}, pluck="name")
	}
	if frappe.get_meta("Item").has_field("custom_código_bionexo"):
		for item in frappe.get_all(
			"Item",
			filters={"custom_código_bionexo": ["in", list(codigos)]},
			fields=["name", "custom_código_bionexo"],
		):
			no_erp.setdefault(item.name, codigos[item.custom_código_bionexo])
	return no_erp


def aderencia(doctype_item: str, parent: str, itens_erp: dict[str, float]) -> tuple[int, int]:
	"""(itens do relatório presentes no documento, desses com a mesma quantidade)."""
	linhas = frappe.get_all(doctype_item, filters={"parent": parent}, fields=["item_code", "qty"])
	qtds = {}
	for linha in linhas:
		qtds[linha.item_code] = qtds.get(linha.item_code, 0) + (linha.qty or 0)
	presentes = [codigo for codigo in itens_erp if codigo in qtds]
	mesma_qtd = sum(1 for codigo in presentes if abs(qtds[codigo] - itens_erp[codigo]) < 1e-6)
	return len(presentes), mesma_qtd


@frappe.whitelist()
def vinculos_da_rfq(request_for_quotation: str) -> dict:
	"""Solicitações de Compras e itens de uma RFQ, para o formulário filtrar e preencher os campos."""
	frappe.has_permission("Request for Quotation", "read", request_for_quotation, throw=True)
	return {
		"material_requests": material_requests_da_rfq(request_for_quotation),
		"item_codes": sorted(
			set(
				frappe.get_all(
					"Request for Quotation Item", filters={"parent": request_for_quotation}, pluck="item_code"
				)
			)
		),
	}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def rfq_por_material_request(doctype, txt, searchfield, start, page_len, filters):
	"""Link query: RFQs submetidas, só as que referenciam a Solicitação de Compras escolhida (se houver)."""
	condicoes = [["docstatus", "=", 1]]
	if filters and filters.get("material_request"):
		condicoes.append(["Request for Quotation Item", "material_request", "=", filters["material_request"]])
	if txt:
		condicoes.append(["name", "like", f"%{txt}%"])
	return frappe.get_list(
		"Request for Quotation",
		filters=condicoes,
		fields=["name", "transaction_date"],
		distinct=True,
		order_by="`tabRequest for Quotation`.creation desc",
		limit_start=start,
		limit_page_length=page_len,
		as_list=True,
	)


@frappe.whitelist()
def criar_fornecedores(importacao: str, cnpjs: str | list | None = None) -> dict:
	"""Cadastra os fornecedores "Não cadastrado" da importação (ou só os CNPJs indicados).

	Usa a consulta de CNPJ do app busca_cnpj quando instalado; se a consulta falhar, cadastra com o nome e o
	CNPJ do relatório. Devolve {"criados": [...], "erros": [...]}.
	"""
	frappe.has_permission("Supplier", "create", throw=True)
	doc = frappe.get_doc("Importacao Bionexo", importacao)
	doc.check_permission("write")
	if doc.docstatus != 0:
		frappe.throw(_("A importação já foi concluída."))
	if isinstance(cnpjs, str):
		cnpjs = json.loads(cnpjs) if cnpjs.startswith("[") else [cnpjs]
	alvo = {normalizar_cnpj(c) for c in cnpjs or []}

	criados, erros = [], []
	for linha in doc.fornecedores:
		if linha.supplier or (alvo and normalizar_cnpj(linha.cnpj) not in alvo):
			continue
		try:
			linha.supplier = fornecedor_por_cnpj(linha.cnpj) or _criar_fornecedor(linha)
			criados.append(linha.supplier)
		except Exception as erro:
			frappe.log_error(
				title="Importacao Bionexo: cadastro de fornecedor", message=frappe.get_traceback()
			)
			erros.append(f"{linha.nome_bionexo} ({linha.cnpj}): {erro}")

	if criados:
		doc.save()
	return {"criados": criados, "erros": erros}


def _criar_fornecedor(linha) -> str:
	dados = None
	if "busca_cnpj" in frappe.get_installed_apps():
		from busca_cnpj.api import buscar_cnpj

		try:
			dados = buscar_cnpj(linha.cnpj)
		except Exception:
			frappe.clear_messages()
			dados = None

	nome = (dados or {}).get("razao_social") or linha.nome_bionexo
	if frappe.db.exists("Supplier", nome):
		nome = f"{nome} - {linha.cnpj}"
	supplier = frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": nome,
			"supplier_type": "Company",
			"tax_id": (dados or {}).get("cnpj_formatado") or linha.cnpj,
			"supplier_group": frappe.db.get_single_value("Buying Settings", "supplier_group"),
			"country": "Brazil" if frappe.db.exists("Country", "Brazil") else None,
		}
	)
	supplier.insert()

	if dados:
		from busca_cnpj.api import confirmar_dados_cnpj

		if not dados.get("email"):
			dados["email"] = linha.email
		return confirmar_dados_cnpj(supplier.name, json.dumps(dados))["supplier"]
	return supplier.name


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def itens_da_importacao(doctype, txt, searchfield, start, page_len, filters):
	"""Link query dos itens do relatório: itens do Pedido de Cotação (ou, sem ele, da Solicitação de Compras),
	com nome e quantidade solicitada."""
	filters = filters or {}
	if filters.get("request_for_quotation"):
		tabela, pai = "Request for Quotation Item", filters["request_for_quotation"]
	elif filters.get("material_request"):
		tabela, pai = "Material Request Item", filters["material_request"]
	else:
		return []
	condicoes = {"parent": pai}
	linhas = frappe.get_all(
		tabela,
		filters=condicoes,
		fields=["item_code", "item_name", "qty", "uom"],
		order_by="idx asc",
	)
	txt = (txt or "").lower()
	return [
		(l.item_code, f"{l.item_name} | {l.qty:g} {l.uom or ''}".strip())
		for l in linhas
		if not txt or txt in l.item_code.lower() or txt in (l.item_name or "").lower()
	][int(start) : int(start) + int(page_len)]


# Documentos que a Importacao Bionexo referencia: a importação é o registro da leitura do PDF e não trava o
# cancelamento nem a exclusão deles (antes, a OC não cancelava por causa da importação enviada e a importação
# não cancelava por causa da OC enviada).
VINCULOS_DA_IMPORTACAO = {
	"Purchase Order": ("Importacao Bionexo Cotacao", "purchase_order"),
	"Supplier Quotation": ("Importacao Bionexo Cotacao", "supplier_quotation"),
	"Request for Quotation": ("Importacao Bionexo", "request_for_quotation"),
	"Material Request": ("Importacao Bionexo", "material_request"),
}


def liberar_cancelamento(doc, method=None):
	"""doc_events on_cancel: ignora a Importacao Bionexo na checagem de vínculos do cancelamento.

	Roda depois do on_cancel do controller (que pode definir ignore_linked_doctypes, como a Purchase Order) e antes
	da checagem do Frappe (check_no_back_links_exist).
	"""
	ignorados = tuple(doc.get("ignore_linked_doctypes") or ())
	if "Importacao Bionexo" not in ignorados:
		doc.ignore_linked_doctypes = (*ignorados, "Importacao Bionexo")


def desvincular_ao_excluir(doc, method=None):
	"""doc_events on_trash: limpa a referência na importação antes da checagem de vínculos da exclusão."""
	tabela, campo = VINCULOS_DA_IMPORTACAO.get(doc.doctype, (None, None))
	if tabela:
		frappe.db.set_value(tabela, {campo: doc.name}, campo, None, update_modified=False)
