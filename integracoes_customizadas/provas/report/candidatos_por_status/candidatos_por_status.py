# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	return columns, data, None, chart


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
			"fieldname": "email",
			"label": _("Email"),
			"fieldtype": "Data",
			"width": 180
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "etapa_atual",
			"label": _("Etapa Atual"),
			"fieldtype": "Link",
			"options": "Interview Round",
			"width": 180
		}
	]


def get_data(filters):
	conditions = ""
	values = {}
	
	if filters.get("edital"):
		conditions += " AND e.name = %(edital)s"
		values["edital"] = filters.get("edital")
	
	if filters.get("status"):
		conditions += " AND ec.status_candidato = %(status)s"
		values["status"] = filters.get("status")
	
	data = frappe.db.sql("""
		SELECT
			e.name as edital,
			e.titulo as titulo_edital,
			ec.job_applicant as candidato,
			ec.applicant_name as nome_candidato,
			ec.email as email,
			ec.status_candidato as status,
			ec.etapa_atual as etapa_atual
		FROM `tabEdital` e
		INNER JOIN `tabEdital Candidato Item` ec ON ec.parent = e.name
		WHERE 1=1 {conditions}
		ORDER BY e.name, ec.status_candidato, ec.applicant_name
	""".format(conditions=conditions), values, as_dict=True)
	
	return data


def get_chart_data(data):
	"""Gera dados para o gráfico de pizza com status dos candidatos."""
	status_count = {}
	for row in data:
		status = row.get("status") or "Sem Status"
		status_count[status] = status_count.get(status, 0) + 1
	
	if not status_count:
		return None
	
	return {
		"data": {
			"labels": list(status_count.keys()),
			"datasets": [
				{
					"values": list(status_count.values())
				}
			]
		},
		"type": "pie",
		"colors": ["#7cd6fd", "#5e64ff", "#ff5858", "#ffa00a"]
	}
