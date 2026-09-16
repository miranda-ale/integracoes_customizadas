"""Ajustes de permissões que precisam persistir após a sincronização dos DocTypes."""

import frappe


def after_migrate():
	if not frappe.db.exists("DocType", "Processo Judicial"):
		return
	for name in frappe.get_all(
		"Custom DocPerm",
		filters={"parent": "Processo Judicial", "role": ["in", ["Usuário Jurídico", "System Manager"]]},
		pluck="name",
	):
		frappe.db.set_value(
			"Custom DocPerm", name, {"create": 0, "write": 1}, update_modified=False
		)
	frappe.clear_cache(doctype="Processo Judicial")
