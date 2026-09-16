"""Ajustes de permissões que precisam persistir após a sincronização dos DocTypes."""

import json

import frappe

from integracoes_customizadas.juridico.datajud import _descricao_movimento


def after_migrate():
	if not frappe.db.exists("DocType", "Processo Judicial"):
		return
	for name in frappe.get_all(
		"Custom DocPerm",
		filters={"parent": "Processo Judicial", "role": ["in", ["Usuário Jurídico", "System Manager"]]},
		pluck="name",
	):
		frappe.db.set_value(
			"Custom DocPerm", name, {"create": 1, "write": 1}, update_modified=False
		)
	if frappe.db.has_column("Processo Judicial", "status_processo"):
		for name in frappe.get_all(
			"Processo Judicial", filters={"status_processo": ["is", "not set"]}, pluck="name"
		):
			frappe.db.set_value(
				"Processo Judicial", name, "status_processo", "Em andamento", update_modified=False
			)
	if frappe.db.has_column("Processo Judicial", "nome_parte"):
		campos = {"Employee": "employee_name", "Customer": "customer_name", "Supplier": "supplier_name", "Terceiros": "full_name"}
		for row in frappe.get_all(
			"Processo Judicial", filters={"parte": ["is", "set"], "nome_parte": ["is", "not set"]},
			fields=["name", "tipo_parte", "parte"],
		):
			if row.tipo_parte in campos:
				doctype = "Contact" if row.tipo_parte == "Terceiros" else row.tipo_parte
				nome = frappe.db.get_value(doctype, row.parte, campos[row.tipo_parte])
				if nome:
					frappe.db.set_value("Processo Judicial", row.name, "nome_parte", nome, update_modified=False)
	if frappe.db.has_column("Processo Judicial", "doctype_parte"):
		for row in frappe.get_all("Processo Judicial", fields=["name", "tipo_parte", "doctype_parte"]):
			doctype = "Contact" if row.tipo_parte == "Terceiros" else row.tipo_parte
			if row.doctype_parte != doctype:
				frappe.db.set_value("Processo Judicial", row.name, "doctype_parte", doctype, update_modified=False)
	if frappe.db.has_column("Processo Judicial Movimento", "descricao"):
		for row in frappe.get_all(
			"Processo Judicial Movimento",
			fields=["name", "nome", "descricao", "complementos_tabelados"],
		):
			try:
				complementos = json.loads(row.complementos_tabelados or "[]")
			except (TypeError, ValueError):
				complementos = []
			descricao = _descricao_movimento({"nome": row.nome, "complementosTabelados": complementos})
			if row.descricao != descricao:
				frappe.db.set_value("Processo Judicial Movimento", row.name, "descricao", descricao, update_modified=False)
	frappe.clear_cache(doctype="Processo Judicial")
