"""Conexões dos processos judiciais nas partes envolvidas."""

from frappe import _


def _adicionar_processos(data, tipo_parte):
	data["fieldname"] = data.get("fieldname") or "parte"
	data.setdefault("non_standard_fieldnames", {})["Processo Judicial"] = "parte"
	data.setdefault("dynamic_links", {})["parte"] = [tipo_parte, "tipo_parte"]
	data.setdefault("transactions", []).append(
		{"label": _("Jurídico"), "items": ["Processo Judicial"]}
	)
	return data


def employee_dashboard(data):
	return _adicionar_processos(data, "Employee")


def customer_dashboard(data):
	return _adicionar_processos(data, "Customer")


def supplier_dashboard(data):
	return _adicionar_processos(data, "Supplier")
