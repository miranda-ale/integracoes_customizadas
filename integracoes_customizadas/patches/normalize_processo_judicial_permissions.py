"""Remove a antiga permissão manual de criação que sobrepõe o DocType padrão."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Processo Judicial"):
		return
	for name in frappe.get_all(
		"Custom DocPerm",
		filters={"parent": "Processo Judicial", "role": "System Manager", "create": 1},
		pluck="name",
	):
		frappe.db.set_value("Custom DocPerm", name, "create", 0, update_modified=False)
	frappe.clear_cache(doctype="Processo Judicial")
