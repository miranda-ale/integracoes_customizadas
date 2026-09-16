"""Permite completar o cadastro e apresenta números antigos com a máscara CNJ."""

import frappe

from integracoes_customizadas.juridico.datajud import _numero_cnj_formatado


def execute():
	if not frappe.db.exists("DocType", "Processo Judicial"):
		return

	for name in frappe.get_all(
		"Custom DocPerm", filters={"parent": "Processo Judicial", "role": ["in", ["Usuário Jurídico", "System Manager"]]}, pluck="name"
	):
		frappe.db.set_value("Custom DocPerm", name, "write", 1, update_modified=False)

	for row in frappe.get_all("Processo Judicial", fields=["name", "numero_processo"]):
		if row.numero_processo and len(row.numero_processo) == 20 and row.numero_processo.isdigit():
			frappe.db.set_value(
				"Processo Judicial", row.name, "numero_processo",
				_numero_cnj_formatado(row.numero_processo), update_modified=False,
			)
	frappe.clear_cache(doctype="Processo Judicial")
