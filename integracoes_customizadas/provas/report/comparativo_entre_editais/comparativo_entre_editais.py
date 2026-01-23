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
			"fieldname": "titulo",
			"label": _("Título"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "vaga",
			"label": _("Vaga"),
			"fieldtype": "Link",
			"options": "Job Opening",
			"width": 150
		},
		{
			"fieldname": "cargo",
			"label": _("Cargo"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "total_candidatos",
			"label": _("Total Candidatos"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "inscritos",
			"label": _("Inscritos"),
			"fieldtype": "Int",
			"width": 80
		},
		{
			"fieldname": "aprovados",
			"label": _("Aprovados"),
			"fieldtype": "Int",
			"width": 80
		},
		{
			"fieldname": "reprovados",
			"label": _("Reprovados"),
			"fieldtype": "Int",
			"width": 80
		},
		{
			"fieldname": "eliminados",
			"label": _("Eliminados"),
			"fieldtype": "Int",
			"width": 80
		},
		{
			"fieldname": "percentual_aprovacao",
			"label": _("% Aprovação"),
			"fieldtype": "Percent",
			"width": 100
		},
		{
			"fieldname": "total_etapas",
			"label": _("Etapas"),
			"fieldtype": "Int",
			"width": 80
		}
	]


def get_data(filters):
	conditions = ""
	values = {}
	
	if filters.get("status"):
		conditions += " AND e.status = %(status)s"
		values["status"] = filters.get("status")
	
	if filters.get("vaga"):
		conditions += " AND e.job_opening = %(vaga)s"
		values["vaga"] = filters.get("vaga")
	
	# Busca editais
	editais = frappe.db.sql("""
		SELECT
			e.name as edital,
			e.titulo,
			e.job_opening as vaga,
			e.designation as cargo,
			e.status,
			(SELECT COUNT(*) FROM `tabEdital Etapa Item` WHERE parent = e.name) as total_etapas
		FROM `tabEdital` e
		WHERE 1=1 {conditions}
		ORDER BY e.modified DESC
	""".format(conditions=conditions), values, as_dict=True)
	
	data = []
	for edital in editais:
		# Conta candidatos por status
		candidatos = frappe.db.sql("""
			SELECT 
				COUNT(*) as total,
				SUM(CASE WHEN status_candidato = 'Inscrito' THEN 1 ELSE 0 END) as inscritos,
				SUM(CASE WHEN status_candidato = 'Aprovado' THEN 1 ELSE 0 END) as aprovados,
				SUM(CASE WHEN status_candidato = 'Reprovado' THEN 1 ELSE 0 END) as reprovados,
				SUM(CASE WHEN status_candidato = 'Eliminado' THEN 1 ELSE 0 END) as eliminados
			FROM `tabEdital Candidato Item`
			WHERE parent = %(edital)s
		""", {"edital": edital.edital}, as_dict=True)[0]
		
		total = candidatos.total or 0
		aprovados = candidatos.aprovados or 0
		
		# Calcula percentual de aprovação
		percentual = (aprovados / total * 100) if total > 0 else 0
		
		data.append({
			"edital": edital.edital,
			"titulo": edital.titulo,
			"vaga": edital.vaga,
			"cargo": edital.cargo,
			"status": edital.status,
			"total_candidatos": total,
			"inscritos": candidatos.inscritos or 0,
			"aprovados": aprovados,
			"reprovados": candidatos.reprovados or 0,
			"eliminados": candidatos.eliminados or 0,
			"percentual_aprovacao": round(percentual, 2),
			"total_etapas": edital.total_etapas or 0
		})
	
	return data


def get_chart_data(data):
	"""Gera dados para o gráfico de barras comparativo."""
	if not data:
		return None
	
	labels = [row.get("titulo", row.get("edital", ""))[:20] for row in data]
	aprovados = [row.get("aprovados", 0) for row in data]
	reprovados = [row.get("reprovados", 0) for row in data]
	inscritos = [row.get("inscritos", 0) for row in data]
	
	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Inscritos"),
					"values": inscritos
				},
				{
					"name": _("Aprovados"),
					"values": aprovados
				},
				{
					"name": _("Reprovados"),
					"values": reprovados
				}
			]
		},
		"type": "bar",
		"colors": ["#7cd6fd", "#5e64ff", "#ff5858"]
	}
