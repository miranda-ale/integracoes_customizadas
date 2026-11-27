import frappe

from integracoes_customizadas.seed.variantes_modelos import VARIANTES


def execute():
	"""Preenche as variantes só nos Modelos WhatsApp que ainda não têm nenhuma (nunca sobrescreve)."""
	for titulo, textos in VARIANTES.items():
		if not frappe.db.exists("Modelo WhatsApp", titulo):
			continue
		modelo = frappe.get_doc("Modelo WhatsApp", titulo)
		if modelo.variantes:
			continue
		for texto in textos:
			modelo.append("variantes", {"mensagem": texto, "ativo": 1, "peso": 1})
		modelo.save(ignore_permissions=True)
