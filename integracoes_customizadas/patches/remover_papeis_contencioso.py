"""Remove os papeis legados do Contencioso (sem uso no codigo; usuarios e perfis nao recebem substituto)."""

import frappe

PAPEIS = ("RH/DP Contencioso", "Financeiro Contencioso")


def execute():
	for papel in PAPEIS:
		if not frappe.db.exists("Role", papel):
			continue
		frappe.db.delete("Has Role", {"role": papel})
		frappe.db.delete("Custom DocPerm", {"role": papel})
		frappe.db.delete("DocPerm", {"role": papel})
		frappe.delete_doc("Role", papel, force=True, ignore_permissions=True)
	frappe.clear_cache()
