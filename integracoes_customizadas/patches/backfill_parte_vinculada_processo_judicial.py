"""Marca como vinculados os processos que já possuem parte cadastrada."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Processo Judicial"):
		return
	frappe.reload_doc("juridico", "doctype", "processo_judicial")
	frappe.db.sql("update `tabProcesso Judicial` set parte_vinculada = 1 where ifnull(parte, '') != ''")
