# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	
	# Adiciona classificação
	data = add_classification(data)
	
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "classificacao",
			"label": _("Classificação"),
			"fieldtype": "Int",
			"width": 100
		},
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
			"width": 180
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
			"fieldname": "etapa_atual",
			"label": _("Etapa Atual"),
			"fieldtype": "Link",
			"options": "Interview Round",
			"width": 180
		},
		{
			"fieldname": "nota",
			"label": _("Nota"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
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
	
	# Ordenar por nota decrescente para classificação
	data = frappe.db.sql("""
		SELECT
			e.name as edital,
			e.titulo as titulo_edital,
			ec.job_applicant as candidato,
			ec.applicant_name as nome_candidato,
			ec.etapa_atual as etapa_atual,
			COALESCE(ec.nota, 0) as nota,
			ec.status_candidato as status
		FROM `tabEdital` e
		INNER JOIN `tabEdital Candidato Item` ec ON ec.parent = e.name
		WHERE ec.status_candidato NOT IN ('Eliminado', 'Reprovado')
		{conditions}
		ORDER BY e.name, ec.nota DESC, ec.applicant_name
	""".format(conditions=conditions), values, as_dict=True)
	
	return data


def add_classification(data):
	"""Adiciona classificação por edital baseado na nota."""
	if not data:
		return data
	
	# Agrupa por edital
	editais = {}
	for row in data:
		edital = row.get("edital")
		if edital not in editais:
			editais[edital] = []
		editais[edital].append(row)
	
	# Adiciona classificação por edital
	result = []
	for edital, candidatos in editais.items():
		# Ordena por nota decrescente
		candidatos_ordenados = sorted(candidatos, key=lambda x: x.get("nota", 0), reverse=True)
		
		for idx, candidato in enumerate(candidatos_ordenados, start=1):
			candidato["classificacao"] = idx
			result.append(candidato)
	
	return result
