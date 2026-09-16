"""Assuntos mais frequentes entre os processos judiciais cadastrados."""

import frappe
from frappe import _


@frappe.whitelist()
def get_data(chart_name=None, **kwargs):
	frappe.has_permission("Processo Judicial", "read", throw=True)

	# O Table MultiSelect armazena um vínculo por assunto e processo.
	rows = frappe.get_list(
		"Processo Judicial Assunto",
		parent_doctype="Processo Judicial",
		fields=["assunto", "COUNT(DISTINCT parent) AS total"],
		filters={"parenttype": "Processo Judicial", "parentfield": "assuntos", "assunto": ["is", "set"]},
		group_by="assunto",
		order_by="total desc, assunto asc",
		limit_page_length=10,
	)
	if not rows:
		return {"labels": [], "datasets": [{"name": _("Processos"), "values": []}]}

	nomes = dict(
		frappe.get_all(
			"Assunto Judicial",
			filters={"name": ["in", [row.assunto for row in rows]]},
			fields=["name", "nome"],
			as_list=True,
		)
	)
	return {
		"labels": [nomes.get(row.assunto) or row.assunto for row in rows],
		"datasets": [{"name": _("Processos"), "values": [row.total for row in rows]}],
	}
