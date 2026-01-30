import frappe
from frappe.utils import today


def atualizar_prazos_vencidos():
	"""Atualiza prazos vencidos (workflow automático)."""
	hoje = today()
	prazos = frappe.get_all(
		"CJ Prazo",
		filters={
			"cj_status_prazo": "A Vencer",
			"cj_data_vencimento": ("<", hoje),
		},
		fields=["name"],
	)
	for prazo in prazos:
		doc = frappe.get_doc("CJ Prazo", prazo.name)
		doc.cj_status_prazo = "Vencido"
		doc.save(ignore_permissions=True)
