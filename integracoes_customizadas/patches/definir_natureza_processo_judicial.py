"""Processos anteriores à classificação interna eram todos de ex-colaboradores: natureza Trabalhista (idempotente)."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Processo Judicial"):
		return
	frappe.reload_doc("juridico", "doctype", "processo_judicial")
	frappe.db.sql(
		"update `tabProcesso Judicial` set natureza = 'Trabalhista' where ifnull(natureza, '') = ''"
	)
