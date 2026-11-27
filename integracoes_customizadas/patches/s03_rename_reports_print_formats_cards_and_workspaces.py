# Copyright (c) 2026, StillPulse Tecnologia LTDA and contributors
# See license.txt

"""Phase 2, wave 2: English prefixed names (`Integ`) for Reports, Print Formats, Dashboard Charts, Number Cards, the Dashboard,
the Workspaces and the Custom HTML Block of the app.

[pre_model_sync]: the standard files are already under the new names. ``frappe.rename_doc`` rewrites links (Has Role, Workspace
links, number cards and charts, Dashboard cards). It does not rewrite text inside a Workspace ``content`` (a JSON string) nor the
Property Setters: the Custom HTML Block name is replaced inside every Workspace content here. Idempotent: a step runs only when the
old name exists exactly (the comparison of the database ignores accents and case) and the new one does not.
"""

import json

import frappe

RENAMES = (
	("Report", "Aging de Processos", "Integ Legal Cases Aging"),
	("Report", "Candidatos por Etapa", "Integ Candidates by Stage"),
	("Report", "Candidatos por Status", "Integ Candidates by Status"),
	("Report", "Comparativo entre Editais", "Integ Notice Comparison"),
	("Report", "Mapa de Precos RFQ", "Integ RFQ Price Map"),
	("Report", "Passivo de Processos", "Integ Legal Cases Liability"),
	("Report", "Pedidos a Receber", "Integ Orders to Receive"),
	("Report", "Processos por Colaborador", "Integ Legal Cases by Employee"),
	("Report", "Provisao de Processos", "Integ Legal Cases Provision"),
	("Report", "Recebidos a Faturar", "Integ Received Not Invoiced"),
	("Report", "Relacao de Processos", "Integ Legal Cases List"),
	("Print Format", "Gabarito", "Integ Exam Answer Key"),
	("Print Format", "Minuta Edital", "Integ Notice Draft"),
	("Print Format", "Prova Completa", "Integ Full Exam"),
	("Dashboard Chart", "Assuntos Judiciais mais Frequentes", "Integ Top Legal Subjects"),
	("Dashboard Chart", "Processos por Fase", "Integ Legal Cases by Phase"),
	("Dashboard Chart", "Processos por Localidade IBGE", "Integ Legal Cases by IBGE Location"),
	("Dashboard Chart", "Processos por Risco", "Integ Legal Cases by Risk"),
	("Dashboard Chart", "Processos por Situação", "Integ Legal Cases by Status"),
	("Dashboard Chart", "Processos por Tribunal", "Integ Legal Cases by Court"),
	("Number Card", "Processos Encerrados", "Integ Closed Legal Cases"),
	("Number Card", "Processos em Andamento", "Integ Ongoing Legal Cases"),
	("Number Card", "Total de Processos Judiciais", "Integ Total Legal Cases"),
	("Dashboard", "Processos Judiciais", "Integ Legal Cases"),
	("Workspace", "Juridico", "Integ Legal"),
	("Workspace", "Provas", "Integ Exams"),
	("Workspace", "Integracoes", "Integ Integrations"),
	("Custom HTML Block", "Relatórios", "Integ Reports"),
)


def _exact(doctype, name):
	return bool(frappe.db.sql(f"select 1 from `tab{doctype}` where name = %s collate utf8mb4_bin", name))


def execute():
	for doctype, old, new in RENAMES:
		if _exact(doctype, old) and not frappe.db.exists(doctype, new):
			frappe.rename_doc(doctype, old, new, force=True, ignore_if_exists=True, show_alert=False)
	_rename_block_in_workspace_contents("Relatórios", "Integ Reports")
	frappe.clear_cache()


def _rename_block_in_workspace_contents(old, new):
	"""Replace the custom block name in the ``content`` of every Workspace that shows it."""
	for name, content in frappe.db.sql(
		"select name, content from `tabWorkspace` where content like %s", f"%{old}%"
	):
		try:
			blocks = json.loads(content or "[]")
		except ValueError:
			continue
		changed = False
		for block in blocks:
			data = block.get("data") or {}
			if block.get("type") == "custom_block" and data.get("custom_block_name") == old:
				data["custom_block_name"] = new
				changed = True
		if changed:
			frappe.db.set_value(
				"Workspace", name, "content", json.dumps(blocks, ensure_ascii=False), update_modified=False
			)
