import frappe


def execute():
	if not frappe.db.exists("Module Def", "Juridico"):
		frappe.get_doc(
			{"doctype": "Module Def", "module_name": "Juridico", "app_name": "integracoes_customizadas"}
		).insert(ignore_permissions=True)
