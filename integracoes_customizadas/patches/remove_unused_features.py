import frappe
from frappe import _


def execute():
	"""Remove metadados de funcionalidades sem adoção comprovada."""
	_remove_contracts()
	_remove_unused_recruitment_fields()
	_remove_scheduled_contract_job()
	frappe.clear_cache()


def _remove_contracts():
	if frappe.db.exists("DocType", "Contrato de Trabalho"):
		contract_count = frappe.db.count("Contrato de Trabalho")
		if contract_count:
			frappe.throw(
				_(
					"A remoção de Contrato de Trabalho foi interrompida porque existem {0} registros."
				).format(contract_count)
			)

	artifacts = {
		"Notification": ["Vencimento de Contrato de Trabalho"],
		"Print Format": ["Contrato de Trabalho"],
		"Report": ["Contratos a vencer / vencidos"],
		"Property Setter": [
			"Contrato de Trabalho-naming_series-options",
			"Contrato de Trabalho-naming_series-default",
		],
	}
	for doctype, names in artifacts.items():
		for name in names:
			frappe.delete_doc(doctype, name, ignore_missing=True, force=True)

	frappe.delete_doc("DocType", "Contrato de Trabalho", ignore_missing=True, force=True)


def _remove_unused_recruitment_fields():
	frappe.delete_doc("Report", "Notas dos Candidatos", ignore_missing=True, force=True)

	for custom_field in ("Interview-prova", "Interview Round-edital"):
		frappe.delete_doc("Custom Field", custom_field, ignore_missing=True, force=True)


def _remove_scheduled_contract_job():
	frappe.delete_doc(
		"Scheduled Job Type",
		"utils.processar_alertas_contratos",
		ignore_missing=True,
		force=True,
	)
