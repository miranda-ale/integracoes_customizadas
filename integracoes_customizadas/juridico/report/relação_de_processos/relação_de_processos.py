"""Relação consultável dos processos judiciais cadastrados."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	query_filters = []
	if filters.get("company"):
		query_filters.append(["Processo Judicial", "empresa", "=", filters.company])
	for field in (
		"tipo_parte", "parte", "fase_processo", "status_processo",
		"situacao_cadastro", "risco", "tribunal", "grau",
	):
		if filters.get(field):
			query_filters.append(["Processo Judicial", field, "=", filters[field]])

	if filters.get("numero_processo"):
		query_filters.append(["Processo Judicial", "numero_processo", "like", f"%{filters.numero_processo}%"])
	if filters.get("assunto"):
		query_filters.append(["Processo Judicial Assunto", "assunto", "=", filters.assunto])
	if filters.get("de"):
		query_filters.append(["Processo Judicial", "data_ajuizamento", ">=", getdate(filters.de)])
	if filters.get("ate"):
		query_filters.append(["Processo Judicial", "data_ajuizamento", "<", frappe.utils.add_days(getdate(filters.ate), 1)])
	if filters.get("de") and filters.get("ate") and getdate(filters.de) > getdate(filters.ate):
		frappe.throw(_("A data inicial não pode ser posterior à data final."))

	fields = [
		"name", "numero_processo", "empresa", "tipo_parte", "parte", "nome_parte",
		"fase_processo", "status_processo", "situacao_cadastro", "risco", "tribunal",
		"grau", "orgao_julgador_nome", "classe_nome", "data_ajuizamento",
		"data_hora_ultima_atualizacao", "valor_causa", "valor_condenacao", "moeda",
	]
	# get_list aplica as permissões do DocType, inclusive ao filtrar pela tabela filha.
	data = frappe.get_list(
		"Processo Judicial", fields=fields, filters=query_filters,
		order_by="data_ajuizamento desc, name asc", limit_page_length=0, distinct=True,
	)
	assuntos = defaultdict(list)
	for start in range(0, len(data), 500):
		names = [row.name for row in data[start:start + 500]]
		for item in frappe.get_all(
			"Processo Judicial Assunto",
			filters={"parent": ["in", names], "parenttype": "Processo Judicial"},
			fields=["parent", "nome", "assunto"], order_by="idx asc",
		):
			assuntos[item.parent].append(item.nome or item.assunto)
	for row in data:
		row.nome_parte = row.nome_parte or row.parte
		row.assuntos = ", ".join(assuntos[row.name])
	return get_columns(), data


def get_columns():
	return [
		{"fieldname": "numero_processo", "label": _("Número do Processo"), "fieldtype": "Data", "width": 195},
		{"fieldname": "empresa", "label": _("Empresa"), "fieldtype": "Link", "options": "Company", "width": 180},
		{"fieldname": "nome_parte", "label": _("Parte"), "fieldtype": "Data", "width": 190},
		{"fieldname": "fase_processo", "label": _("Fase"), "fieldtype": "Data", "width": 110},
		{"fieldname": "status_processo", "label": _("Situação"), "fieldtype": "Data", "width": 125},
		{"fieldname": "tribunal", "label": _("Tribunal"), "fieldtype": "Data", "width": 95},
		{"fieldname": "classe_nome", "label": _("Classe"), "fieldtype": "Data", "width": 200},
		{"fieldname": "assuntos", "label": _("Assuntos"), "fieldtype": "Data", "width": 230},
		{"fieldname": "data_ajuizamento", "label": _("Ajuizamento"), "fieldtype": "Datetime", "width": 150},
		{"fieldname": "risco", "label": _("Risco"), "fieldtype": "Data", "width": 90},
		{"fieldname": "valor_causa", "label": _("Valor da Causa"), "fieldtype": "Currency", "options": "moeda", "width": 140},
	]
