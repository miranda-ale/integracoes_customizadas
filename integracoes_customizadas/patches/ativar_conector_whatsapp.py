import frappe


def execute():
	"""Conector ativo nas instalações existentes: o campo `ativo` é novo e sem valor gravado."""
	if frappe.db.get_single_value("Configuracoes WhatsApp", "ativo") is None:
		frappe.db.set_single_value("Configuracoes WhatsApp", "ativo", 1)
