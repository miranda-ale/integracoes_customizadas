# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
	"""Cria Custom Fields necessários para o módulo de Provas."""
	create_interview_custom_fields()


def create_interview_custom_fields():
	"""Cria o Custom Field 'prova' no DocType Interview."""
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
