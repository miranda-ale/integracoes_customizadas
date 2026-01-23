# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "edital",
			"label": _("Edital"),
			"fieldtype": "Link",
			"options": "Edital",
			"width": 150
		},
		{
			"fieldname": "titulo_edital",
			"label": _("Título do Edital"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "etapa",
			"label": _("Etapa"),
			"fieldtype": "Link",
			"options": "Interview Round",
			"width": 200
		},
		{
			"fieldname": "ordem_etapa",
			"label": _("Ordem"),
			"fieldtype": "Int",
			"width": 80
		},
		{
			"fieldname": "candidato",
			"label": _("Candidato"),
			"fieldtype": "Link",
			"options": "Job Applicant",
			"width": 150
		},
		{
			"fieldname": "nome_candidato",
			"label": _("Nome do Candidato"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "nota",
			"label": _("Nota"),
			"fieldtype": "Float",
			"width": 80
		}
	]


def get_data(filters):
	conditions = ""
	values = {}
	
	if filters.get("edital"):
		conditions += " AND e.name = %(edital)s"
		values["edital"] = filters.get("edital")
	
	if filters.get("etapa"):
		conditions += " AND ec.etapa_atual = %(etapa)s"
		values["etapa"] = filters.get("etapa")
	
	if filters.get("status"):
		conditions += " AND ec.status_candidato = %(status)s"
		values["status"] = filters.get("status")
	
	data = frappe.db.sql("""
		SELECT
			e.name as edital,
			e.titulo as titulo_edital,
			ec.etapa_atual as etapa,
			COALESCE(ee.ordem, 0) as ordem_etapa,
			ec.job_applicant as candidato,
			ec.applicant_name as nome_candidato,
			ec.status_candidato as status,
			ec.nota as nota
		FROM `tabEdital` e
		INNER JOIN `tabEdital Candidato Item` ec ON ec.parent = e.name
		LEFT JOIN `tabEdital Etapa Item` ee ON ee.parent = e.name AND ee.interview_round = ec.etapa_atual
		WHERE 1=1 {conditions}
		ORDER BY e.name, ee.ordem, ec.applicant_name
	""".format(conditions=conditions), values, as_dict=True)
	
	return data


@frappe.whitelist()
def get_filter_options():
	"""Retorna opções para os filtros do relatório."""
	editais = frappe.get_all("Edital", fields=["name", "titulo"])
	etapas = frappe.get_all("Interview Round", fields=["name"])
	
	return {
		"editais": editais,
		"etapas": etapas,
		"status": ["Inscrito", "Aprovado", "Reprovado", "Eliminado"]
	}
