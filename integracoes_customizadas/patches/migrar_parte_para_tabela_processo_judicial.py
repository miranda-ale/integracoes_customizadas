"""Migra a parte atual de cada processo judicial para a tabela de partes (idempotente)."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Processo Judicial"):
		return
	frappe.reload_doc("juridico", "doctype", "processo_judicial_parte")
	frappe.reload_doc("juridico", "doctype", "processo_judicial")
	for processo in frappe.get_all(
		"Processo Judicial",
		or_filters={"tipo_parte": ["is", "set"], "parte": ["is", "set"], "nome_parte": ["is", "set"], "cpf_parte": ["is", "set"]},
		fields=["name", "tipo_parte", "doctype_parte", "parte", "nome_parte", "cpf_parte"],
	):
		if frappe.db.exists("Processo Judicial Parte", {"parent": processo.name, "parenttype": "Processo Judicial"}):
			continue
		frappe.get_doc(
			{
				"doctype": "Processo Judicial Parte",
				"parent": processo.name,
				"parenttype": "Processo Judicial",
				"parentfield": "partes",
				"idx": 1,
				"papel": "Reclamante",
				"tipo_parte": processo.tipo_parte,
				"doctype_parte": processo.doctype_parte,
				"parte": processo.parte,
				"nome": processo.nome_parte,
				"documento": processo.cpf_parte,
				"principal": 1,
			}
		).db_insert()
