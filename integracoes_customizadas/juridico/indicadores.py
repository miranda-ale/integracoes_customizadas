"""Indicadores do painel do workspace Juridico (Custom HTML Block "Juridico Indicadores")."""

import frappe
from frappe.utils import add_days, flt, getdate, today

PROCESSO = "Processo Judicial"
PARECER = "CLM Legal Evaluation"
DIAS_SEM_ATUALIZACAO = 90
DIAS_NOVOS = 30
TOP_ASSUNTOS = 5


def _filtros(company, extra=None):
	filtros = dict(extra or {})
	if company:
		filtros["empresa"] = company
	return filtros


def _contar(doctype, filtros):
	return frappe.get_list(doctype, filters=filtros, fields=["count(name) as total"])[0].total


def _por_status(company):
	linhas = frappe.get_list(
		PROCESSO,
		filters=_filtros(company),
		fields=["status_processo", "count(name) as total", "sum(valor_causa) as valor"],
		group_by="status_processo",
	)
	andamento = encerrados = 0
	valor_andamento = 0.0
	for linha in linhas:
		if linha.status_processo == "Encerrado":
			encerrados += linha.total
		else:
			andamento += linha.total
			valor_andamento += flt(linha.valor)
	return andamento, encerrados, valor_andamento


def _top_assuntos(company):
	filtros = {"parenttype": PROCESSO, "parentfield": "assuntos", "assunto": ["is", "set"]}
	if company:
		pais = frappe.get_list(PROCESSO, filters=_filtros(company), pluck="name", limit_page_length=0)
		if not pais:
			return []
		filtros["parent"] = ["in", pais]
	linhas = frappe.get_list(
		"Processo Judicial Assunto",
		parent_doctype=PROCESSO,
		fields=["assunto", "COUNT(DISTINCT parent) AS total"],
		filters=filtros,
		group_by="assunto",
		order_by="total desc, assunto asc",
		limit_page_length=TOP_ASSUNTOS,
	)
	nomes = dict(
		frappe.get_all(
			"Assunto Judicial",
			filters={"name": ["in", [r.assunto for r in linhas]]},
			fields=["name", "nome"],
			as_list=True,
		)
	)
	return [{"assunto": nomes.get(r.assunto) or r.assunto, "total": r.total} for r in linhas]


def _pareceres(company):
	"""Pareceres Juridicos do CLM; None quando o app nao existe ou o usuario nao le o DocType."""
	if not frappe.db.exists("DocType", PARECER) or not frappe.has_permission(PARECER, "read"):
		return None
	filtros = {"company": company} if company else {}
	linhas = frappe.get_list(
		PARECER, filters=filtros, fields=["docstatus", "count(name) as total"], group_by="docstatus"
	)
	por_status = {linha.docstatus: linha.total for linha in linhas}
	return {
		"rascunho": por_status.get(0, 0),
		"emitidos": por_status.get(1, 0),
		"cancelados": por_status.get(2, 0),
	}


@frappe.whitelist()
def get_dashboard(company: str | None = None) -> dict:
	frappe.has_permission(PROCESSO, "read", throw=True)
	if company:
		frappe.has_permission("Company", doc=company, throw=True)

	hoje = getdate(today())
	andamento, encerrados, valor_andamento = _por_status(company)
	em_andamento = {"status_processo": ["!=", "Encerrado"]}
	limite = add_days(hoje, -DIAS_SEM_ATUALIZACAO)

	return {
		"referencia": hoje.strftime("%d/%m/%Y"),
		"dias_sem_atualizacao": DIAS_SEM_ATUALIZACAO,
		"dias_novos": DIAS_NOVOS,
		"andamento": andamento,
		"encerrados": encerrados,
		"total": andamento + encerrados,
		"valor_andamento": valor_andamento,
		"novos": _contar(PROCESSO, _filtros(company, {"creation": [">=", add_days(hoje, -DIAS_NOVOS)]})),
		"sem_atualizacao": _contar(
			PROCESSO,
			_filtros(
				company,
				{**em_andamento, "data_hora_ultima_atualizacao": ["<", limite]},
			),
		),
		"risco_alto": _contar(PROCESSO, _filtros(company, {**em_andamento, "risco": "Alto"})),
		"rascunhos": _contar(PROCESSO, _filtros(company, {"situacao_cadastro": "Rascunho"})),
		"assuntos": _top_assuntos(company),
		"pareceres": _pareceres(company),
	}
