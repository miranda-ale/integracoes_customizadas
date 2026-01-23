# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
	"""Cria Custom Fields necessários para o módulo de Provas."""
	create_interview_custom_fields()


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
