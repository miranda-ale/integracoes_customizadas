# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
	"""Cria Custom Fields necessários para o módulo de Provas."""
	create_interview_custom_fields()
	create_edital_custom_fields()


def create_interview_custom_fields():
	"""Cria o Custom Field 'prova' no DocType Interview."""
	try:
		# Verifica se o DocType Interview existe
		if not frappe.db.exists("DocType", "Interview"):
			frappe.log_error("DocType 'Interview' não encontrado. Custom Field 'prova' não pode ser criado.")
			return

		custom_fields = {
			"Interview": [
				{
					"fieldname": "prova",
					"fieldtype": "Link",
					"label": "Prova",
					"options": "Prova",
					"insert_after": "interview_round",
					"depends_on": "eval:doc.interview_type=='Prova de Conhecimentos Gerais e Específicos'",
					"description": "Prova vinculada a este Interview",
				},
				{
					"fieldname": "edital",
					"fieldtype": "Link",
					"label": "Edital",
					"options": "Edital",
					"insert_after": "prova",
					"description": "Edital vinculado a este Interview",
				}
			]
		}

		create_custom_fields(custom_fields, update=True)
		frappe.db.commit()

		# Verifica se o campo foi criado corretamente
		custom_field_exists = frappe.db.exists(
			"Custom Field",
			{"dt": "Interview", "fieldname": "prova"}
		)

		if not custom_field_exists:
			frappe.log_error("Falha ao criar Custom Field 'prova' no DocType 'Interview'.")

	except Exception as e:
		frappe.log_error(f"Erro ao criar Custom Field 'prova' no DocType 'Interview': {str(e)}")
		raise


def create_edital_custom_fields():
	"""Cria Custom Fields para conexão bidirecional com Edital."""
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
		
		# Custom Field 'edital' em Interview Round
		if frappe.db.exists("DocType", "Interview Round"):
			custom_fields["Interview Round"] = [
				{
					"fieldname": "edital",
					"fieldtype": "Link",
					"label": "Edital",
					"options": "Edital",
					"insert_after": "designation",
					"description": "Edital vinculado a esta etapa",
				}
			]
		
		if custom_fields:
			create_custom_fields(custom_fields, update=True)
			frappe.db.commit()
			
	except Exception as e:
		frappe.log_error(f"Erro ao criar Custom Fields para Edital: {str(e)}")
		raise


def verify_interview_custom_field():
	"""Verifica se o Custom Field 'prova' existe no DocType Interview."""
	if not frappe.db.exists("DocType", "Interview"):
		return False

	custom_field_exists = frappe.db.exists(
		"Custom Field",
		{"dt": "Interview", "fieldname": "prova"}
	)

	if not custom_field_exists:
		# Tenta recriar o campo
		try:
			create_interview_custom_fields()
		except Exception as e:
			frappe.log_error(f"Erro ao recriar Custom Field 'prova': {str(e)}")
			return False

	return True


def verify_edital_custom_fields():
	"""Verifica se os Custom Fields para conexão bidirecional com Edital existem."""
	fields_ok = True
	
	# Verifica Job Applicant
	if frappe.db.exists("DocType", "Job Applicant"):
		if not frappe.db.exists("Custom Field", {"dt": "Job Applicant", "fieldname": "edital"}):
			fields_ok = False
	
	# Verifica Interview Round
	if frappe.db.exists("DocType", "Interview Round"):
		if not frappe.db.exists("Custom Field", {"dt": "Interview Round", "fieldname": "edital"}):
			fields_ok = False
	
	# Verifica Interview
	if frappe.db.exists("DocType", "Interview"):
		if not frappe.db.exists("Custom Field", {"dt": "Interview", "fieldname": "edital"}):
			fields_ok = False
	
	if not fields_ok:
		try:
			create_edital_custom_fields()
			create_interview_custom_fields()
		except Exception as e:
			frappe.log_error(f"Erro ao recriar Custom Fields para Edital: {str(e)}")
			return False
	
	return True


def after_migrate():
	"""Cria Custom Fields após cada migração do banco de dados."""
	try:
		create_interview_custom_fields()
		create_edital_custom_fields()
		remover_link_prova_edital_invalido()
	except Exception as e:
		frappe.log_error(f"Erro ao criar Custom Fields durante migração: {str(e)}")


@frappe.whitelist()
def criar_custom_fields_edital():
	"""Método whitelisted para criar Custom Fields manualmente via console ou API."""
	try:
		create_interview_custom_fields()
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
