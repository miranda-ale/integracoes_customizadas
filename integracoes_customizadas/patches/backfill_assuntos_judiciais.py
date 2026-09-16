"""Preenche o catálogo de assuntos para processos criados antes do multiselect."""

import frappe

from integracoes_customizadas.juridico.datajud import _registrar_assunto


def execute():
	if not frappe.db.exists("DocType", "Processo Judicial Assunto"):
		return
	for row in frappe.get_all(
		"Processo Judicial Assunto", fields=["name", "codigo", "nome", "assunto"]
	):
		if row.assunto:
			continue
		frappe.db.set_value(
			"Processo Judicial Assunto", row.name, "assunto",
			_registrar_assunto(row.codigo, row.nome), update_modified=False,
		)
