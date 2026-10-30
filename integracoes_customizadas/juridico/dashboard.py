"""Conexões dos processos judiciais nas partes envolvidas."""

import frappe
from frappe import _
from frappe.desk.notifications import get_open_count as _get_open_count

TIPOS_PARTE = {"Employee": "Employee", "Customer": "Customer", "Supplier": "Supplier", "Contact": "Terceiros"}


def _adicionar_processos(data, tipo_parte):
	data["fieldname"] = data.get("fieldname") or "parte"
	data.setdefault("non_standard_fieldnames", {})["Processo Judicial"] = "parte"
	data.setdefault("dynamic_links", {})["parte"] = [tipo_parte, "tipo_parte"]
	data.setdefault("transactions", []).append({"label": _("Jurídico"), "items": ["Processo Judicial"]})
	return data


def employee_dashboard(data):
	return _adicionar_processos(data, "Employee")


def customer_dashboard(data):
	return _adicionar_processos(data, "Customer")


def supplier_dashboard(data):
	return _adicionar_processos(data, "Supplier")


def contact_dashboard(data):
	return _adicionar_processos(data, "Terceiros")


@frappe.whitelist()
@frappe.read_only()
def get_open_count(doctype: str, name: str | int, items=None):
	"""Conexões padrão do Frappe, contando também processos em que a parte não é a principal.

	O filtro do dashboard só alcança campos do próprio Processo Judicial (a principal espelhada);
	as demais partes ficam na tabela filha e são somadas aqui.
	"""
	resultado = _get_open_count(doctype, name, items)
	tipo_parte = TIPOS_PARTE.get(doctype)
	if not tipo_parte or not isinstance(resultado.get("count"), dict):
		return resultado
	externos = resultado["count"].setdefault("external_links_found", [])
	# Quando "items" restringe as transações, só soma se Processo Judicial foi pedido.
	if items is not None and "Processo Judicial" not in (frappe.parse_json(items) if isinstance(items, str) else items):
		return resultado
	processos = set(
		frappe.get_all(
			"Processo Judicial Parte",
			filters={
				"parenttype": "Processo Judicial",
				"parentfield": "partes",
				"doctype_parte": doctype,
				"parte": name,
			},
			pluck="parent",
			limit=100,
		)
	)
	atual = next((item for item in externos if item["doctype"] == "Processo Judicial"), None)
	if atual is None and not processos:
		return resultado
	if atual is None:
		atual = {"doctype": "Processo Judicial", "count": 0, "open_count": 0}
		externos.append(atual)
	if processos and isinstance(atual["count"], int):
		principais = set(
			frappe.get_all(
				"Processo Judicial", filters={"parte": name, "tipo_parte": tipo_parte}, pluck="name", limit=100
			)
		)
		atual["count"] = len(principais | processos)
	return resultado
