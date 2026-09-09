# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
	"""Cria Custom Fields necessários para o módulo de Provas."""
	create_edital_custom_fields()


def create_edital_custom_fields():
	"""Cria os vínculos com Edital efetivamente usados pelo recrutamento."""
	try:
		custom_fields = {}
		
		# Custom Field 'edital' em Job Applicant
		if frappe.db.exists("DocType", "Job Applicant"):
			custom_fields["Job Applicant"] = [
				{
					"fieldname": "edital",
					"fieldtype": "Link",
					"label": "Edital",
					"options": "Edital",
					"insert_after": "job_title",
					"description": "Edital vinculado a este candidato",
				}
			]
		
		# Custom Field 'edital' em Interview
		if frappe.db.exists("DocType", "Interview"):
			custom_fields["Interview"] = [
				{
					"fieldname": "edital",
					"fieldtype": "Link",
					"label": "Edital",
					"options": "Edital",
					"insert_after": "interview_round",
					"description": "Edital vinculado a esta entrevista",
				}
			]
		
		if custom_fields:
			create_custom_fields(custom_fields, update=True)
			frappe.db.commit()
			
	except Exception as e:
		frappe.log_error(f"Erro ao criar Custom Fields para Edital: {str(e)}")
		raise


def verify_edital_custom_fields():
	"""Verifica os vínculos com Edital usados por candidatos e entrevistas."""
	fields_ok = True
	
	# Verifica Job Applicant
	if frappe.db.exists("DocType", "Job Applicant"):
		if not frappe.db.exists("Custom Field", {"dt": "Job Applicant", "fieldname": "edital"}):
			fields_ok = False
	
	# Verifica Interview
	if frappe.db.exists("DocType", "Interview"):
		if not frappe.db.exists("Custom Field", {"dt": "Interview", "fieldname": "edital"}):
			fields_ok = False
	
	if not fields_ok:
		try:
			create_edital_custom_fields()
		except Exception as e:
			frappe.log_error(f"Erro ao recriar Custom Fields para Edital: {str(e)}")
			return False
	
	return True


def after_migrate():
	"""Cria Custom Fields após cada migração do banco de dados."""
	try:
		create_edital_custom_fields()
		remover_link_prova_edital_invalido()
	except Exception as e:
		frappe.log_error(f"Erro ao criar Custom Fields durante migração: {str(e)}")


@frappe.whitelist()
def criar_custom_fields_edital():
	"""Método whitelisted para criar Custom Fields manualmente via console ou API."""
	try:
		create_edital_custom_fields()
		remover_link_prova_edital_invalido()
		frappe.msgprint("Custom Fields criados com sucesso!", indicator="green", title="Sucesso")
		return {"success": True, "message": "Custom Fields criados com sucesso"}
	except Exception as e:
		frappe.log_error(f"Erro ao criar Custom Fields: {str(e)}")
		return {"success": False, "message": str(e)}


def remover_link_prova_edital_invalido():
	"""Remove link inválido Prova -> Edital que causa erro de coluna inexistente."""
	try:
		exists = frappe.db.exists(
			"DocType Link",
			{
				"parent": "Prova",
				"parenttype": "DocType",
				"parentfield": "links",
				"link_doctype": "Edital",
				"link_fieldname": "edital",
			},
		)
		if exists:
			frappe.db.delete(
				"DocType Link",
				{
					"parent": "Prova",
					"parenttype": "DocType",
					"parentfield": "links",
					"link_doctype": "Edital",
					"link_fieldname": "edital",
				},
			)
			frappe.db.commit()
	except Exception:
		pass
